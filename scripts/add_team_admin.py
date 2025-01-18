"""
python ../scripts/add_team_admin.py <project_name> <username>
"""

import sys

sys.path.append("../")
sys.path.append("../backend")

import sys
import argparse
from sqlalchemy import select
from backend.db.database import SessionLocal
from backend.db.models import Project, User, TeamMember, TeamRole


def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    while True:
        response = input(f"{message} [y/N]: ").lower().strip()
        if response in ["y", "yes"]:
            return True
        if response in ["", "n", "no"]:
            return False


def select_project(projects):
    """Let user select from multiple matching projects."""
    print("\nMultiple matching projects found:")
    for idx, project in enumerate(projects, 1):
        print(f"{idx}. {project.name} (id: {project.id})")

    while True:
        try:
            choice = input("\nSelect project number (or 'q' to quit): ")
            if choice.lower() == "q":
                sys.exit(0)

            idx = int(choice)
            if 1 <= idx <= len(projects):
                return projects[idx - 1]
            print("Invalid selection. Please try again.")
        except ValueError:
            print("Please enter a valid number.")


def add_team_admin(project_name: str, username: str):
    """Add a user as an admin to the team associated with a project.

    Args:
        project_name: Name of the project (case insensitive)
        username: Username of the user to add as admin
    """
    db = SessionLocal()

    try:
        # Find project using case-insensitive search
        projects = (
            db.execute(select(Project).where(Project.name.ilike(project_name)))
            .scalars()
            .all()
        )

        if not projects:
            print(f"Error: Project '{project_name}' not found", file=sys.stderr)
            sys.exit(1)

        # If multiple projects found, let user select
        project = projects[0] if len(projects) == 1 else select_project(projects)

        # Find user
        user = db.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if not user:
            print(f"Error: User '{username}' not found", file=sys.stderr)
            sys.exit(1)

        # Check if user is already a member
        existing_member = db.execute(
            select(TeamMember).where(
                TeamMember.team_id == project.team_id, TeamMember.user_id == user.id
            )
        ).scalar_one_or_none()

        if existing_member:
            print(
                f"Error: User '{username}' is already a member of this team",
                file=sys.stderr,
            )
            sys.exit(1)

        # Confirm action
        if not confirm_action(
            f"Add user '{username}' as admin to team for project '{project.name}'?"
        ):
            print("Operation cancelled")
            sys.exit(0)

        # Add user as admin
        team_member = TeamMember(
            team_id=project.team_id, user_id=user.id, role=TeamRole.ADMIN
        )
        db.add(team_member)
        db.commit()

        print(
            f"Successfully added '{username}' as admin to team for project '{project.name}'"
        )

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Add a user as an admin to the team associated with a project"
    )
    parser.add_argument("project_name", help="Name of the project (case insensitive)")
    parser.add_argument("username", help="Username of the user to add as admin")

    args = parser.parse_args()
    add_team_admin(args.project_name, args.username)


if __name__ == "__main__":
    main()
