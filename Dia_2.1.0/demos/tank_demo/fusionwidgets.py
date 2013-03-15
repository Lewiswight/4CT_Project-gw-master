"""\
"""

# imports
from common.types.boolean import Boolean
from settings.settings_base import SettingsBase, Setting
from presentations.presentation_base import PresentationBase
import digiweb


class FusionWidgets(PresentationBase):
    def __init__(self, name, core_services):
        self.__name = name
        self.__core = core_services
        self.__cdb = \
            self.__core.get_service("channel_manager").channel_database_get()
        
        settings_list = [
            Setting(
                name='mount_on_dir', type=str, required=False,
                default_value='/fusionwidgets'),
        ]

        ## Initialize settings:
        PresentationBase.__init__(self, name=name,
                                    settings_list=settings_list)

    def apply_settings(self):
        SettingsBase.apply_settings(self)

    def start(self):
        self._cb_handle = digiweb.Callback(self.cb)

    def stop(self):
        del self._cb_handle

    def cb(self, type, path, headers, args):
        print "FUSION: entered digiweb cb"
        mount_on_dir = SettingsBase.get_setting(self, 'mount_on_dir')
        if not path.startswith(mount_on_dir):
            return None

        # Paths should look like /mount_on_dir/get/channel_name
        try:
            root, mount_on_dir, action, channel_name = path.split('/')
        except:
            return None

        print "FUSION: action = '%s', channel_name = '%s'" % (action, channel_name)

        try:
            channel = self.__cdb.channel_get(channel_name)

            if action == "get":
                value = channel.get().value
                # Special type handling:
                if isinstance(value, bool) or isinstance(value, Boolean):
                    value = int(value)
                value = str(value)
                html = "&value=%s" % (value)
                print "FUSION: returning '%s'" % (html)
                return (digiweb.TextHtml, html)

        except Exception, e:
            print "FUSION exception: %s" % (str(e))


        return None

