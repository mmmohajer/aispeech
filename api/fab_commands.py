from fabric import task

from config.utils.role_based import build_group_list
from ai.utils.test import test_ai_manager

@task
def buildgrouplist(ctx):
    build_group_list()

@task
def testaimanager(ctx):
    test_ai_manager()