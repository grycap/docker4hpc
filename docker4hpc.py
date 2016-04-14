#!/usr/bin/env python
import sys
import os
import grp
import pwd
import ConfigParser
import logging

def to_boolean(value):
    if value is None:
        return False
    if str(value).upper in [ "YES", "TRUE" ]:
        return True
    return False

def read_section(config, section):
    values_section = {}
    if section not in config.sections():
        return values_section
    
    options = config.options(section)
    for option in options:
        value = config.get(section, option)
        if value == "":
            value = None
        values_section[option] = value
    return values_section

def set_defaults(values):
    if 'clean_map_file' in values:
        values['clean_map_file'] = to_boolean(values['clean_map_file'])
    else:
        values['clean_map_file'] = False
    
    if 'clean_map_folder' in values:
        values['clean_map_folder'] = to_boolean(values['clean_map_folder'])
    else:
        values['clean_map_folder'] = False

    if 'clean_map_device' in values:
        values['clean_map_device'] = to_boolean(values['clean_map_device'])
    else:
        values['clean_map_device'] = False

def build_config_tree(config_files = ["/etc/docker4hpc.cfg"]):
    config = ConfigParser.ConfigParser()
    config.read(config_files)
    CONFIG_TREE = {}
    KEYWORDS=[ "USER", "APP", "QUEUE" ]
    for kw in KEYWORDS:
        section_prefix=("%s " % kw)
        L = len(section_prefix)

        values = {}
        for section_name in config.sections():
            if (section_name[0:L] == section_prefix):
                element_name = (section_name[L:]).strip()
                values[element_name] = read_section(config, section_name)
                set_defaults(values)
            
        CONFIG_TREE[kw] = values
        
    KEYWORDS=[ "DEFAULTS", "USERIMAGES", "APPIMAGES", "QUEUEIMAGES" ]
    for section_name in KEYWORDS:
        CONFIG_TREE[section_name] = read_section(config, section_name)

    if "USERIMAGES" in config.sections():
        options = config.options("USERIMAGES")
        for username in options:
            if username not in CONFIG_TREE["USER"]:
                CONFIG_TREE["USER"][username] = {}
            docker_image = config.get("USERIMAGES", username)
            if 'docker_image' not in CONFIG_TREE["USER"][username]:
                CONFIG_TREE["USER"][username]['docker_image'] = docker_image
            if CONFIG_TREE["USER"][username]['docker_image'] != docker_image:
                logging.warning("Overlapping docker image for user %s. Using the image in the specific section." % username)

    if "APPIMAGES" in config.sections():
        options = config.options("APPIMAGES")
        for appname in options:
            if appname not in CONFIG_TREE["APP"]:
                CONFIG_TREE["APP"][appname] = {}
            docker_image = config.get("APPIMAGES", appname)
            if 'docker_image' not in CONFIG_TREE["APP"][appname]:
                CONFIG_TREE["APP"][appname]['docker_image'] = docker_image
            if CONFIG_TREE["APP"][appname]['docker_image'] != docker_image:
                logging.warning("Overlapping docker image for app %s. Using the image in the specific section." % appname)

    if "QUEUEIMAGES" in config.sections():
        options = config.options("QUEUEIMAGES")
        for queuename in options:
            if queuename not in CONFIG_TREE["QUEUE"]:
                CONFIG_TREE["QUEUE"][queuename] = {}
            docker_image = config.get("QUEUEIMAGES", queuename)
            if 'docker_image' not in CONFIG_TREE["QUEUE"][queuename]:
                CONFIG_TREE["QUEUE"][queuename]['docker_image'] = docker_image
            if CONFIG_TREE["QUEUE"][queuename]['docker_image'] != docker_image:
                logging.warning("Overlapping docker image for queue %s. Using the image in the specific section." % queuename)

    return CONFIG_TREE

def get_values_for_prefix(options, prefix):
    values = []
    L = len(prefix)
    for option in options:
        if (option is not None) and option[0:L] == prefix:
            value = options[option]
            if value is not None:
                values.append(value.strip())
    return values

def get_setting(setting_name, settings_collection):
    for s in settings_collection:
        if setting_name in s and s[setting_name] is not None:
            return s[setting_name]
    return None

def gather_setting(setting_name, settings_collection):
    gathered = []
    for s in settings_collection:
        if (setting_name in s) and (s[setting_name] is not None):
            gathered = gathered + s[setting_name]
    return gathered

CONFIG_TREE = build_config_tree()

DEFAULT_IMAGE="ubuntu:latest"
    
class User_info:
    def __init__(self):
        self.username = self._get_username()
        self.group, self.groups = self._get_groups()
        self.homedir = os.environ['HOME']
    
    def _get_username(self):
        uid = os.getuid()
        try:
            username = pwd.getpwuid(uid).pw_name
        except:
            username = None
            
        return username
    
    def _get_groups(self):
        gids = os.getgroups()
        groups = []
        
        for gid in gids:
            try:
                groups.append(grp.getgrgid(gid).gr_name)
            except:
                pass
        
        group = None
        try:
            group = grp.getgrgid(os.getgid()).gr_name
        except: pass
        
        return group, groups

class DockerCMDLine_generator:
    def __init__(self, script = ""):
        self.userinfo = User_info()
        self.docker_options = []
        self.docker_binary = "docker"
        self.docker_image = None
        self.docker_script = script

    def _pre_process(self):
        pass

    def _generate_docker_script(self):
        pass

    def get(self):
        self._pre_process()
        self._generate_docker_script()
        
        cmdline = "%s run %s %s bash -c '%s'" % (self.docker_binary, " ".join(self.docker_options), self.docker_image, self.docker_script)
        return cmdline

class DockerCMDLine_generator_PBS(DockerCMDLine_generator):
    def __init__(self):
        DockerCMDLine_generator.__init__(self, "")
        self._run_lines = []
        self._header_lines = [ ]
        self._pbs_options = {}
        
        self._SETTINGS = None
        self._working_dir = None

    def get_header(self):
        return "\n".join(self._header_lines)

    def _pre_process(self):
        self._run_lines = []
        self._header_lines = [ ]
        self._pbs_options = {}
        self._SETTINGS = None
        self._working_dir = None
        
        # We are processing the stdin (as it is piped through this script by torque)
        for line in sys.stdin:
            line = line.rstrip("\n").strip()
            if line[0:4] == "#PBS":
                # This will be used to select resources in PBS
                self._header_lines.append(line)
                
                # Now get the option for PBS
                option = line[4:].strip().split(" ", 2)
                while len(option) < 2:
                    option.append(None)
                
                flag, value = option
                if flag is not None:
                    self._pbs_options[flag] = value
                
            else:
                self._run_lines.append(line)

        queue = None
        if '-q' in self._pbs_options:
            queue = self._pbs_options['-q']
            
        #If the -q option is specified, it is in one of the following three forms:
        #queue
        #@server
        #queue@server

        # Now we could decide the container name according to the queue or the userinfo
        
        
        #-u user_list
        #Defines the user name under which the job is to run on the execution system.
        #The user_list argument is of the form:
        #
        #user[@host][,user[@host],...]
        #Only one user name may be given per specified host. Only one of the user specifications may be supplied without the corresponding host specification. That user name will used for execution on any host not named in the argument list. If unset, the user list defaults to the user who is running qsub.

        #-d path
        #Defines the working directory path to be used for the job. If the -d option is not specified, the default working directory is the home directory. This option sets the environment variable PBS_O_INITDIR.
        if '-d' in self._pbs_options:
            self._working_dir = self._pbs_options['-d']
            
        #-D path
        #Defines the root directory to be used for the job. This option sets the environment variable PBS_O_ROOTDIR.
        
        # WORKING_DIR = $HOME
        # 
        
        
        DEFAULT_SETTINGS = {}
        set_defaults(DEFAULT_SETTINGS)
        
        options = CONFIG_TREE["DEFAULTS"]
        for option in options:
            DEFAULT_SETTINGS[option] = options[option]
        DEFAULT_SETTINGS["map_file"] = get_values_for_prefix(options, "map_file")
        DEFAULT_SETTINGS["map_folder"] = get_values_for_prefix(options, "map_folder")
        DEFAULT_SETTINGS["map_device"] = get_values_for_prefix(options, "map_device")
        DEFAULT_SETTINGS["docker_options"] = get_values_for_prefix(options, "docker_options")        
        
        QUEUE_SETTINGS = {}
        set_defaults(QUEUE_SETTINGS)
        if queue is not None:
            if queue in CONFIG_TREE["QUEUE"]:
                options = CONFIG_TREE["QUEUE"][queue]
                for option in options:
                    QUEUE_SETTINGS[option] = options[option]
                QUEUE_SETTINGS["map_file"] = get_values_for_prefix(options, "map_file")
                QUEUE_SETTINGS["map_folder"] = get_values_for_prefix(options, "map_folder")
                QUEUE_SETTINGS["map_device"] = get_values_for_prefix(options, "map_device")
                QUEUE_SETTINGS["docker_options"] = get_values_for_prefix(options, "docker_options")
                
        USER_SETTINGS = {}
        set_defaults(USER_SETTINGS)
        
        username = self.userinfo.username
        if username is not None:
            if username in CONFIG_TREE["USER"]:
                options = CONFIG_TREE["USER"][username]
                for option in options:
                    USER_SETTINGS[option] = options[option]
                USER_SETTINGS["map_file"] = get_values_for_prefix(options, "map_file")
                USER_SETTINGS["map_folder"] = get_values_for_prefix(options, "map_folder")
                USER_SETTINGS["map_device"] = get_values_for_prefix(options, "map_device")
                USER_SETTINGS["docker_options"] = get_values_for_prefix(options, "docker_options")
        
        APP_NAMES = CONFIG_TREE["APP"].keys()
        APP_SETTINGS = {
            'docker_image': None,
            'docker_options': None,
            'map_file': None,
            'map_folder': None,
            'map_device': None
        }
        set_defaults(APP_SETTINGS)
        
        for l in self._run_lines:
            for app_name in APP_NAMES:
                pos_shebang = l.find("#")
                if pos_shebang >= 0:
                    l = l[0:pos_shebang]
                l = l.strip()
                pos = l.find(app_name)
                if pos >= 0:
                    context = l[max(0, pos - 1) : pos + len(app_name) + 1]
                    if context.strip() == app_name:
                        options = CONFIG_TREE["APP"][app_name]
                        for option in options:
                            if options[option] is not None:
                                if (option in APP_SETTINGS) and (APP_SETTINGS[option] is not None) and (APP_SETTINGS[option] != options[option]):
                                    raise Exception("multiple applications with specific containers or overlapping options found in the execution script")
                                APP_SETTINGS[option] = options[option]
                        APP_SETTINGS["map_file"] = get_values_for_prefix(options, "map_file")
                        APP_SETTINGS["map_folder"] = get_values_for_prefix(options, "map_folder")
                        APP_SETTINGS["map_device"] = get_values_for_prefix(options, "map_device")
                        APP_SETTINGS["docker_options"] = get_values_for_prefix(options, "docker_options")
                        
        self._SETTINGS = {
            'docker_image': None,
            'docker_options': None,
            'map_file': None,
            'map_folder': None,
            'map_device': None
        }
        
        if QUEUE_SETTINGS["clean_map_file"]:
            DEFAULT_SETTINGS["map_file"] = []
        if QUEUE_SETTINGS["clean_map_folder"]:
            DEFAULT_SETTINGS["map_folder"] = []
        if QUEUE_SETTINGS["clean_map_device"]:
            DEFAULT_SETTINGS["map_device"] = []

        if USER_SETTINGS["clean_map_file"]:
            QUEUE_SETTINGS["map_file"] = []
            DEFAULT_SETTINGS["map_file"] = []
        if USER_SETTINGS["clean_map_folder"]:
            QUEUE_SETTINGS ["map_folder"] = []
            DEFAULT_SETTINGS["map_folder"] = []
        if USER_SETTINGS["clean_map_device"]:
            QUEUE_SETTINGS["map_device"] = []
            DEFAULT_SETTINGS ["map_device"] = []

        if APP_SETTINGS["clean_map_file"]:
            USER_SETTINGS["map_file"] = []
            QUEUE_SETTINGS["map_file"] = []
            DEFAULT_SETTINGS["map_file"] = []
        if APP_SETTINGS["clean_map_folder"]:
            USER_SETTINGS ["map_folder"] = []
            QUEUE_SETTINGS ["map_folder"] = []
            DEFAULT_SETTINGS["map_folder"] = []
        if APP_SETTINGS["clean_map_device"]:
            USER_SETTINGS["map_device"] = []
            QUEUE_SETTINGS["map_device"] = []
            DEFAULT_SETTINGS ["map_device"] = []
        
        
        self._SETTINGS['docker_image'] = get_setting('docker_image', [APP_SETTINGS, QUEUE_SETTINGS, USER_SETTINGS, DEFAULT_SETTINGS])
        self._SETTINGS['docker_options'] = gather_setting('docker_options', [APP_SETTINGS, QUEUE_SETTINGS, USER_SETTINGS, DEFAULT_SETTINGS])
        self._SETTINGS['map_file'] = gather_setting('map_file', [APP_SETTINGS, QUEUE_SETTINGS, USER_SETTINGS, DEFAULT_SETTINGS])        
        self._SETTINGS['map_folder'] = gather_setting('map_folder', [APP_SETTINGS, QUEUE_SETTINGS, USER_SETTINGS, DEFAULT_SETTINGS])        
        self._SETTINGS['map_device'] = gather_setting('map_device', [APP_SETTINGS, QUEUE_SETTINGS, USER_SETTINGS, DEFAULT_SETTINGS])        
    
    def _generate_docker_script(self):
        if self._SETTINGS['docker_image'] is not None:
            self.docker_image = self._SETTINGS['docker_image']
        else:
            self.docker_image = DEFAULT_IMAGE
            
        for mf in self._SETTINGS['map_file'] + self._SETTINGS['map_folder']:
            docker_opt = "-v \"%s:%s\"" % (mf, mf)
            self.docker_options.append(docker_opt)
            
        for do in self._SETTINGS['docker_options']:
            self.docker_options.append(do)
            
        self.docker_options.append("-u %s" % self.userinfo.username)
        
        if self._working_dir is None:
            self.docker_options.append("-w \"%s\"" % self.userinfo.homedir)
        else:
            self.docker_options.append("-w \"%s\"" % self._working_dir)
        
        self.docker_script = "\n".join(self._run_lines)

if __name__ == '__main__':

    cmdline = DockerCMDLine_generator_PBS()
    print cmdline.get()
    print cmdline.get_header()
    