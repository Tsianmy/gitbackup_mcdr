import mcdreforged.api.all as MCDR
import re
import time

from typing import Optional
from git_backup import common as GL
from git_backup.constants import (Prefix, CONFIG_FILE, PLUGIN_ABBR,
                                  TRIGGER_BACKUP_EVENT, TRIGGER_RESTORE_EVENT)
from git_backup.config import Configure
from git_backup.ops import (create_backup, restore_backup, push_backup, list_backup,
                            prune_backup, command_run, get_backup_info)
from git_backup.git import setup_git
from git_backup.utils import debug_message, tr, print_message

HelpMessage: MCDR.RTextBase

######## MCDR Events ########

def on_load(server: MCDR.PluginServerInterface, old):
    global HelpMessage
    GL.server_inst = server
    if hasattr(old, 'operation_lock') and type(old.operation_lock) == type(GL.operation_lock):
        GL.operation_lock = old.operation_lock

    meta = server.get_self_metadata()
    HelpMessage = tr('help_message', Prefix, meta.name, meta.version)

    load_config(server)

    if GL.config.enabled:
        setup_git(GL.config, logger=server.logger)
        save_config(server)

        register_command(server)
        register_event_listeners(server)
        server.register_help_message(Prefix, command_run(tr('register.summary_help'), tr('register.show_help'), Prefix))
    else:
        server.logger.warning(
            f'{meta.name} is not active, got config.enabled: {GL.config.enabled}')
    
    debug_message(GL.config.debug, 'git_cfg.is_setup:', GL.config.git_cfg['is_setup'])
    # GL.config.enabled = True
    # server.logger.info(f'Set config.enabled = True')

def on_unload(server):
    GL.abort_restore = True
    GL.plugin_unloaded = True
    save_config(server)

def on_info(server: MCDR.PluginServerInterface, info: MCDR.Info):
    if not info.is_user:
        if info.content in GL.config.saved_world_keywords:
            GL.game_saved = True

######## Commands ########

def register_command(server: MCDR.PluginServerInterface):
    def get_literal_node(literal):
        lvl = GL.config.minimum_permission_level.get(literal, 0)
        return MCDR.Literal(literal).requires(lambda src: src.has_permission(lvl)).on_error(MCDR.RequirementNotMet, lambda src: src.reply(tr('command.permission_denied')), handled=True)

    server.register_command(
        MCDR.Literal(Prefix).
        runs(cmd_help_message).
        on_error(MCDR.UnknownArgument, print_unknown_argument_message, handled=True).
        then(
            get_literal_node('make').
            runs(lambda src: cmd_create_backup(src, None)).
            then(MCDR.GreedyText('comment').runs(lambda src, ctx: cmd_create_backup(src, ctx['comment'])))
        ).
        then(
            get_literal_node('back').
            runs(lambda src: cmd_restore_backup(src, ':1')).
            then(MCDR.Text('slot').runs(lambda src, ctx: cmd_restore_backup(src, ctx['slot'])))
        ).
        then(get_literal_node('confirm').runs(cmd_confirm_restore)).
        then(get_literal_node('abort').runs(cmd_trigger_abort)).
        then(get_literal_node('list').runs(lambda src: cmd_list_backup(src))).
        then(get_literal_node('push').runs(lambda src: cmd_push_backup(src))).
        then(get_literal_node('prune').runs(lambda src: cmd_prune_backup(src)))
    )

def cmd_help_message(source: MCDR.CommandSource):
    if source.is_player:
        source.reply('')
    with source.preferred_language_context():
        for line in HelpMessage.to_plain_text().splitlines():
            prefix = re.search(r'(?<=§7){}[\w ]*(?=§)'.format(Prefix), line)
            if prefix is not None:
                print_message(source, MCDR.RText(line).set_click_event(
                    MCDR.RAction.suggest_command, prefix.group()), prefix='')
            else:
                print_message(source, line, prefix='')
        # list_backup(source, size_display=False).join()
        print_message(
            source,
            tr('print_help.hotbar') +
            '\n' +
            MCDR.RText(tr('print_help.click_to_create.text'))
                .h(tr('print_help.click_to_create.hover'))
                .c(MCDR.RAction.suggest_command, tr('print_help.click_to_create.command', Prefix).to_plain_text()) +
            '\n' +
            MCDR.RText(tr('print_help.click_to_restore.text'))
                .h(tr('print_help.click_to_restore.hover'))
                .c(MCDR.RAction.suggest_command, tr('print_help.click_to_restore.command', Prefix).to_plain_text()),
            prefix=''
        )

@MCDR.new_thread(f'{PLUGIN_ABBR} - create')
def cmd_create_backup(source: MCDR.CommandSource, comment: Optional[str]):
    create_backup(source, comment, GL.config, logger=GL.server_inst.logger)
    if GL.config.push_interval > 0 and GL.config.last_push_time + GL.config.push_interval < time.time():
        print_message(source, f'There are out {GL.config.push_interval} sec not push, pushing now...', tell=False)
        push_backup(source, GL.config, logger=GL.server_inst.logger)

def cmd_restore_backup(source: MCDR.CommandSource, bid: str or int):
    try:
        slot, date, comment = get_backup_info(
            GL.config, int(bid[1:]) if isinstance(bid, str) and bid[0] == ':' else bid)
    except RuntimeError as e:
        print_message(source, tr('restore_backup.get_info.fail', e), tell=False)
        GL.slot_selected = None
        GL.date_selected = None
        GL.comment_selected = None
        return

    GL.slot_selected = slot
    GL.date_selected = date
    GL.comment_selected = comment
    GL.abort_restore = False
    print_message(source, tr('restore_backup.echo_action', slot, date, comment), tell=False)
    print_message(
        source,
        command_run(tr('restore_backup.confirm_hint', Prefix), tr('restore_backup.confirm_hover'), '{0} confirm'.format(Prefix))
        + ', '
        + command_run(tr('restore_backup.abort_hint', Prefix), tr('restore_backup.abort_hover'), '{0} abort'.format(Prefix))
        , tell=False
    )

@MCDR.new_thread(f'{PLUGIN_ABBR} - restore')
def cmd_confirm_restore(source: MCDR.CommandSource):
    if GL.slot_selected is None:
        print_message(source, tr('confirm_restore.nothing_to_confirm'), tell=False)
    else:
        slot = GL.slot_selected
        date = GL.date_selected
        comment = GL.comment_selected
        GL.slot_selected = None
        GL.date_selected = None
        GL.comment_selected = None

        restore_backup(source, (slot, date, comment), GL.config, logger=GL.server_inst.logger)

def cmd_trigger_abort(source: MCDR.CommandSource):
    GL.abort_restore = True
    GL.slot_selected = None
    GL.date_selected = None
    GL.comment_selected = None
    print_message(source, tr('trigger_abort.abort'), tell=False)

@MCDR.new_thread(f'{PLUGIN_ABBR} - list')
def cmd_list_backup(source: MCDR.CommandSource, limit: int = None):
    list_backup(source, GL.config, limit=limit)

@MCDR.new_thread(f'{PLUGIN_ABBR} - push')
def cmd_push_backup(source: MCDR.CommandSource):
    push_backup(source, GL.config, logger=GL.server_inst.logger)

@MCDR.new_thread(f'{PLUGIN_ABBR} - prune')
def cmd_prune_backup(source: MCDR.CommandSource):
    prune_backup(source, GL.config, logger=GL.server_inst.logger)

######## Utils ########

def print_unknown_argument_message(source: MCDR.CommandSource, error: MCDR.UnknownArgument):
    print_message(source, command_run(
        tr('unknown_command.text', Prefix),
        tr('unknown_command.hover'),
        Prefix
    ))

def register_event_listeners(server: MCDR.PluginServerInterface):
    server.register_event_listener(TRIGGER_BACKUP_EVENT, lambda svr, source, comment, config, logger: create_backup(source, comment, config, logger))
    server.register_event_listener(TRIGGER_RESTORE_EVENT, lambda svr, source, slot, config, logger: restore_backup(source, slot, config, logger))

def load_config(server: MCDR.ServerInterface, source: MCDR.CommandSource or None = None):
    GL.config = server.load_config_simple(CONFIG_FILE, target_class=Configure,
                                          in_data_folder=False, source_to_reply=source)

def save_config(server: MCDR.ServerInterface):
    server.save_config_simple(GL.config, CONFIG_FILE, in_data_folder=False)