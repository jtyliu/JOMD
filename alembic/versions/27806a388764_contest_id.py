"""Add contest id

Revision ID: 27806a388764
Revises: 83344019a25b
Create Date: 2021-07-13 21:58:46.555273

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27806a388764'
down_revision = '83344019a25b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('participation_solution', sa.Column('contest_id', sa.String(), nullable=True))
    op.create_foreign_key(None, 'participation_solution', 'contest', ['contest_id'], ['key'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'participation_solution', type_='foreignkey')
    op.drop_column('participation_solution', 'contest_id')
    # ### end Alembic commands ###
