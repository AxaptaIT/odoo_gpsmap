from . import controllers
from . import models
from . import wizard


def uninstall_hook(env):
    env['unifiedtalk.gpsmap.account'].deactivate()
