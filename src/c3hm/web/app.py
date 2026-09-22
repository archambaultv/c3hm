"""
Application Flask : interface web de c3hm.
"""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from pathlib import Path
from threading import Timer

from flask import Flask, abort, redirect, render_template, request, url_for

from c3hm.export import (
    ExportError,
    export_notes,
    export_rubric_markdown,
    export_rubric_pdf,
    feedback_html,
    gather,
    omnivox_rows,
    ready_grades,
    rubric_markdown,
)
from c3hm.markup import render_markdown
from c3hm.model import (
    Evaluation,
    Notes,
    Student,
    compute_grade,
    invalid_references,
    level_color,
    merge_notes,
    round_half_up,
    teams,
)
from c3hm.omnivox import OmnivoxError, decode_csv, merge_students, parse_students_csv
from c3hm.storage import Workspace, WorkspaceError, dump_yaml
from c3hm.web.forms import apply_action, parse_evaluation_form, parse_number


def run_server(root: Path, port: int, open_browser: bool = True) -> None:
    app = create_app(Workspace(root))
    if open_browser:
        Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    app.run(host="localhost", port=port, debug=False)


@dataclass
class Subject:
    """Ce que l'on corrige : un étudiant ou une équipe."""

    kind: str  # "etudiant" ou "equipe"
    key: str  # matricule ou nom d'équipe
    title: str
    student: Student | None
    team: str | None  # équipe de l'étudiant, ou nom de l'équipe
    members: list[Student]
    siblings: list[tuple[str, str]]  # (titre, url) pour la navigation
    index: int

    @property
    def base(self) -> str:
        return f"/{self.kind}/{self.key}"

    @property
    def previous(self) -> tuple[str, str] | None:
        return self.siblings[self.index - 1] if self.index > 0 else None

    @property
    def following(self) -> tuple[str, str] | None:
        return self.siblings[self.index + 1] if self.index + 1 < len(self.siblings) else None


def create_app(workspace: Workspace) -> Flask:
    app = Flask(__name__)
    app.config["WORKSPACE"] = workspace

    @app.context_processor
    def inject_globals():
        return {"workspace": workspace, "level_color": level_color, "round_half_up": round_half_up}

    app.jinja_env.filters["md"] = render_markdown

    # --- accueil -------------------------------------------------------------

    @app.get("/")
    def index():
        evaluation: Evaluation | None = None
        error: str | None = None
        if workspace.has_evaluation():
            try:
                evaluation = workspace.load_evaluation()
            except WorkspaceError as e:
                error = str(e)
        try:
            students = workspace.load_students()
            students_error = None
        except WorkspaceError as e:
            students, students_error = [], str(e)
        rows = []
        team_cache: dict[str, Notes | None] = {}
        for student in students:
            try:
                grade = None
                if evaluation:
                    own = workspace.load_notes(student.matricule)
                    if student.team:
                        if student.team not in team_cache:
                            team_cache[student.team] = workspace.load_team_notes(student.team)
                        own = merge_notes(team_cache[student.team], own)  # type: ignore[arg-type]
                    grade = compute_grade(evaluation, own)
                rows.append({"student": student, "grade": grade, "error": None})
            except WorkspaceError as e:
                rows.append({"student": student, "grade": None, "error": str(e)})
        groups: list[dict] = []
        for name in teams(students):
            groups.append({"team": name, "rows": [r for r in rows if r["student"].team == name]})
        solo = [r for r in rows if not r["student"].team]
        if solo:
            groups.append({"team": None, "rows": solo})
        graded_count = sum(1 for r in rows if r["grade"] is not None and r["grade"].complete)
        return render_template(
            "index.html",
            evaluation=evaluation,
            errors=evaluation.validate() if evaluation else [],
            error=error,
            rows=rows,
            groups=groups,
            students_error=students_error,
            graded_count=graded_count,
        )

    # --- évaluation ----------------------------------------------------------

    @app.post("/evaluation/creer")
    def evaluation_create():
        if not workspace.has_evaluation():
            workspace.create_evaluation()
        return redirect(url_for("evaluation_edit"))

    @app.get("/evaluation")
    def evaluation_edit():
        try:
            evaluation = workspace.load_evaluation()
        except WorkspaceError as e:
            text = workspace.read_evaluation_text() if workspace.has_evaluation() else ""
            return render_template("evaluation_error.html", error=str(e), yaml_text=text), 200
        return render_template("evaluation.html", **_form_context(evaluation, saved=False, validate=False))

    @app.post("/evaluation/form")
    def evaluation_form():
        """Recalcule le formulaire à partir des valeurs saisies, sans enregistrer."""
        evaluation = parse_evaluation_form(request.form)
        action = request.form.get("action", "")
        if action:
            apply_action(evaluation, action)
        return render_template("partials/evaluation_form.html", **_form_context(evaluation, saved=False))

    @app.post("/evaluation")
    def evaluation_save():
        evaluation = parse_evaluation_form(request.form)
        errors = evaluation.validate()
        if errors:
            return render_template(
                "partials/evaluation_form.html", **_form_context(evaluation, saved=False, errors=errors)
            )
        affected = _notes_broken_by(evaluation)
        if affected and not request.form.get("confirmer"):
            return render_template(
                "partials/evaluation_form.html", **_form_context(evaluation, saved=False, errors=[], affected=affected)
            )
        workspace.save_evaluation(evaluation)
        return render_template("partials/evaluation_form.html", **_form_context(evaluation, saved=True, errors=[]))

    def _notes_broken_by(new_evaluation: Evaluation) -> list[str]:
        """Étudiants dont les notes sont valides avec la grille actuelle mais pas avec la nouvelle."""
        try:
            current = workspace.load_evaluation() if workspace.has_evaluation() else None
        except WorkspaceError:
            current = None
        names = {s.matricule: s.fullname() for s in _safe_students()}
        candidates = [(names.get(m, m), lambda m=m: workspace.load_notes(m)) for m in workspace.notes_matricules()]
        candidates += [(f"équipe {t}", lambda t=t: workspace.load_team_notes(t)) for t in workspace.team_notes_names()]
        affected = []
        for label, loader in candidates:
            try:
                notes = loader()
            except WorkspaceError:
                continue
            if current is not None and invalid_references(current, notes):
                continue  # déjà invalide, ce n'est pas ce changement qui casse
            if invalid_references(new_evaluation, notes):
                affected.append(label)
        return affected

    def _safe_students() -> list[Student]:
        try:
            return workspace.load_students()
        except WorkspaceError:
            return []

    # --- étudiants -----------------------------------------------------------

    @app.get("/etudiants")
    def students_page():
        return render_template("etudiants.html", **_students_context())

    @app.post("/etudiants/importer")
    def students_import():
        upload = request.files.get("csv")
        if upload is None or not upload.filename:
            return render_template("partials/etudiants.html", **_students_context(error="Aucun fichier choisi."))
        try:
            text = decode_csv(upload.read())
            imported = parse_students_csv(text)
            existing = workspace.load_students()
            merged, new_count = merge_students(existing, imported)
            workspace.save_students(merged)
        except (OmnivoxError, WorkspaceError) as e:
            return render_template("partials/etudiants.html", **_students_context(error=str(e)))
        message = f"{len(imported)} étudiant(s) lus dans {upload.filename}, {new_count} nouveau(x)."
        return render_template("partials/etudiants.html", **_students_context(message=message))

    @app.post("/etudiants/equipe")
    def students_set_team():
        matricule = request.form.get("matricule", "")
        team = request.form.get("equipe", "").strip() or None
        try:
            if team:
                workspace.team_notes_path(team)  # valide le nom
            students = workspace.load_students()
            student = next((s for s in students if s.matricule == matricule), None)
            if student is None:
                abort(404)
            student.team = team
            workspace.save_students(students)
        except WorkspaceError as e:
            return render_template("partials/saved.html", error=str(e))
        return render_template("partials/saved.html")

    def _students_context(message: str | None = None, error: str | None = None) -> dict:
        students = []
        if error is None:
            try:
                students = workspace.load_students()
            except WorkspaceError as e:
                error = str(e)
        return {"students": students, "teams": list(teams(students)), "message": message, "error": error}

    # --- grille et exports ---------------------------------------------------

    @app.get("/exports")
    def exports_page():
        return render_template("exports.html", **_exports_context())

    def _exports_context(report=None, error=None, written=None) -> dict:
        markdown = ""
        omnivox = ""
        try:
            markdown = rubric_markdown(workspace.load_evaluation())
            omnivox = omnivox_rows(ready_grades(workspace))
        except (ExportError, WorkspaceError) as e:
            error = error or str(e)
        return {
            "report": report,
            "error": error,
            "written": written,
            "markdown": markdown,
            "omnivox": omnivox,
        }

    @app.post("/exports/notes")
    def exports_notes():
        try:
            report = export_notes(workspace)
        except (ExportError, WorkspaceError) as e:
            return render_template("partials/exports.html", **_exports_context(error=str(e)))
        return render_template("partials/exports.html", **_exports_context(report=report))

    @app.post("/exports/grille-markdown")
    def exports_rubric_markdown():
        try:
            path = export_rubric_markdown(workspace)
        except (ExportError, WorkspaceError) as e:
            return render_template("partials/exports.html", **_exports_context(error=str(e)))
        return render_template("partials/exports.html", **_exports_context(written=path))

    @app.post("/exports/grille-pdf")
    def exports_rubric_pdf():
        try:
            path = export_rubric_pdf(workspace)
        except (ExportError, WorkspaceError) as e:
            return render_template("partials/exports.html", **_exports_context(error=str(e)))
        return render_template("partials/exports.html", **_exports_context(written=path))

    @app.get("/etudiant/<key>/retroaction")
    def feedback_preview(key: str):
        evaluation = workspace.load_evaluation()
        item = next((g for g in gather(workspace, evaluation) if g.student.matricule == key), None)
        if item is None:
            abort(404)
        return feedback_html(evaluation, item)

    # --- correction ----------------------------------------------------------

    def _subject(kind: str, key: str) -> Subject:
        """
        Sujet à corriger. La navigation précédent/suivant ne circule qu'entre les équipes et les
        étudiants sans équipe ; un membre d'équipe s'atteint depuis la page de son équipe.
        """
        students = workspace.load_students()
        all_teams = teams(students)

        top_level = [(f"Équipe {n}", url_for("grading_page", kind="equipe", key=n)) for n in all_teams]
        solo = [s for s in students if not s.team]
        top_level += [(s.fullname(), url_for("grading_page", kind="etudiant", key=s.matricule)) for s in solo]

        if kind == "etudiant":
            student = next((s for s in students if s.matricule == key), None)
            if student is None:
                abort(404)
            index = -1 if student.team else len(all_teams) + solo.index(student)
            return Subject(
                kind="etudiant",
                key=key,
                title=student.fullname(),
                student=student,
                team=student.team,
                members=all_teams[student.team] if student.team else [],
                siblings=[] if student.team else top_level,
                index=index,
            )
        if key not in all_teams:
            abort(404)
        return Subject(
            kind="equipe",
            key=key,
            title=f"Équipe {key}",
            student=None,
            team=key,
            members=all_teams[key],
            siblings=top_level,
            index=list(all_teams).index(key),
        )

    def _load_own(subject: Subject) -> Notes:
        if subject.kind == "etudiant":
            return workspace.load_notes(subject.key)
        return workspace.load_team_notes(subject.key)

    def _save_own(subject: Subject, notes: Notes) -> None:
        if subject.kind == "etudiant":
            workspace.save_notes(subject.key, notes)
        else:
            workspace.save_team_notes(subject.key, notes)

    def _version(subject: Subject) -> str:
        if subject.kind == "etudiant":
            return workspace.notes_version(matricule=subject.key, team=subject.team)
        return workspace.notes_version(team=subject.key)

    def _notes_context(subject: Subject, **extra) -> dict:
        evaluation = workspace.load_evaluation()
        own = _load_own(subject)
        team_notes = workspace.load_team_notes(subject.team) if subject.kind == "etudiant" and subject.team else None
        effective = merge_notes(team_notes, own) if team_notes is not None else own
        return {
            "subject": subject,
            "base": subject.base,
            "student": subject.student,
            "evaluation": evaluation,
            "notes": effective,
            "own": own,
            "team_notes": team_notes,
            "grade": compute_grade(evaluation, effective),
            "version": _version(subject),
            **extra,
        }

    @app.get("/<any(etudiant, equipe):kind>/<key>")
    def grading_page(kind: str, key: str):
        subject = _subject(kind, key)
        try:
            evaluation = workspace.load_evaluation()
        except WorkspaceError as e:
            return render_template("notes_error.html", subject=subject, error=str(e))
        errors = evaluation.validate()
        if errors:
            return render_template("notes_error.html", subject=subject, errors=errors)
        try:
            ctx = _notes_context(subject)
        except WorkspaceError as e:
            return render_template("notes_error.html", subject=subject, error=str(e))
        return render_template("notes.html", **ctx)

    @app.get("/<any(etudiant, equipe):kind>/<key>/notes")
    def grading_poll(kind: str, key: str):
        """Surveille le disque : 204 si rien n'a changé, sinon une bannière (ou la section si on recharge)."""
        subject = _subject(kind, key)
        if request.args.get("recharger"):
            return render_template("partials/recharger.html", **_notes_context(subject))
        version = _version(subject)
        if request.args.get("v") == version:
            return "", 204
        return render_template("partials/banniere.html", base=subject.base, version=version)

    @app.get("/<any(etudiant, equipe):kind>/<key>/surveiller")
    def grading_poll_resume(kind: str, key: str):
        """Reprend la surveillance en ignorant le changement signalé."""
        subject = _subject(kind, key)
        return render_template(
            "partials/poll.html", base=subject.base, version=request.args.get("v", _version(subject))
        )

    @app.post("/<any(etudiant, equipe):kind>/<key>/niveau")
    def grading_set_level(kind: str, key: str):
        subject = _subject(kind, key)
        own = _load_own(subject)
        own.set_level(request.form.get("critere", ""), request.form.get("niveau") or None)
        _save_own(subject, own)
        return render_template("partials/grille.html", oob_poll=True, **_notes_context(subject))

    @app.post("/<any(etudiant, equipe):kind>/<key>/commentaire")
    def grading_set_comment(kind: str, key: str):
        subject = _subject(kind, key)
        own = _load_own(subject)
        text = request.form.get("texte", "")
        criterion = request.form.get("critere")
        if criterion:
            own.set_comment(criterion, text)
        else:
            own.comment = text.strip()
        _save_own(subject, own)
        ctx = _notes_context(subject)
        team_notes = ctx["team_notes"]
        inherited = team_notes is not None and (
            bool(team_notes.comment_for(criterion)) if criterion else bool(team_notes.comment.strip())
        )
        return render_template("partials/saved.html", inherited=inherited and not text.strip(), **ctx)

    @app.post("/etudiant/<key>/note-ajustee")
    def grading_set_override(key: str):
        subject = _subject("etudiant", key)
        own = _load_own(subject)
        value = parse_number(request.form.get("note", ""))
        if value == "":
            own.override = None
        elif isinstance(value, int | float) and 0 <= value <= 100:
            own.override = value
        else:
            return render_template("partials/saved.html", error="Nombre entre 0 et 100", **_notes_context(subject))
        _save_own(subject, own)
        return render_template("partials/saved.html", oob_grille=True, **_notes_context(subject))

    return app


def _form_context(
    evaluation: Evaluation,
    saved: bool,
    errors: list[str] | None = None,
    validate: bool = True,
    affected: list[str] | None = None,
) -> dict:
    if errors is None:
        errors = evaluation.validate() if validate else []
    return {
        "evaluation": evaluation,
        "errors": errors,
        "saved": saved,
        "affected": affected or [],
        "yaml_text": dump_yaml(evaluation.to_dict()),
    }
