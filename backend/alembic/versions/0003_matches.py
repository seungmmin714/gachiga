"""matches and match_members tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geometry

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("pickup_name", sa.String(100), nullable=False),
        sa.Column("pickup_lat", sa.Float(), nullable=False),
        sa.Column("pickup_lng", sa.Float(), nullable=False),
        sa.Column(
            "pickup_point",
            Geometry("POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("estimated_fare_total", sa.Integer(), nullable=False),
        sa.Column("detour_index", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_matches_status", "matches", ["status"])

    op.create_table(
        "match_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("match_id", sa.Integer(), sa.ForeignKey("matches.id"), nullable=False),
        sa.Column(
            "ride_request_id", sa.Integer(), sa.ForeignKey("ride_requests.id"), nullable=False
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("share_amount", sa.Integer(), nullable=False),
        sa.Column("solo_fare", sa.Integer(), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_match_members_match_id", "match_members", ["match_id"])
    op.create_index("ix_match_members_ride_request_id", "match_members", ["ride_request_id"])
    op.create_index("ix_match_members_user_id", "match_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("match_members")
    op.drop_table("matches")
