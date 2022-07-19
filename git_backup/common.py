import mcdreforged.api.all as MCDR
from threading import Lock
from git_backup.config import Configure

server_inst: MCDR.PluginServerInterface
config: Configure

operation_lock = Lock()
operation_name = MCDR.RText('?')

game_saved: bool = False
abort_restore: bool = False
plugin_unloaded: bool = False
slot_selected: str = None
date_selected: str = None
comment_selected: str = None