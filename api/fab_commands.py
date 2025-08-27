from fabric import task

from config.utils.role_based import build_group_list
from ai.utils.test import test_ai_manager
from app.utils.test import make_teaching_data_ready_for_user

@task
def buildgrouplist(ctx):
    build_group_list()

@task
def testaimanager(ctx):
    test_ai_manager()

@task
def maketeachingdata(ctx):
    make_teaching_data_ready_for_user()