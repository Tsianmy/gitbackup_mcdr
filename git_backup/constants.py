import os
from mcdreforged.api.event import LiteralEvent

PLUGIN_ID = 'git_backup'
Prefix = '!!gbk'
PLUGIN_ABBR = 'GBU'
CONFIG_FILE = os.path.join('config', 'GitBackUp.json')

BACKUP_DONE_EVENT 		= LiteralEvent('{}.backup_done'.format(PLUGIN_ID))
RESTORE_DONE_EVENT 		= LiteralEvent('{}.restore_done'.format(PLUGIN_ID))
TRIGGER_BACKUP_EVENT 	= LiteralEvent('{}.trigger_backup'.format(PLUGIN_ID))
TRIGGER_RESTORE_EVENT 	= LiteralEvent('{}.trigger_restore'.format(PLUGIN_ID))