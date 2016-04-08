#!/usr/bin/env python
import sys
import os
import grp
import pwd

DEFAULT_IMAGE="ubuntu:latest"
    
class User_info:
    def __init__(self):
        self.username = self._get_username()
        self.group, self.groups = self._get_groups()
    
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

    def _decide_docker_image(self):
        if self.docker_image is None:
            self.docker_image = DEFAULT_IMAGE

    def _pre_process(self):
        pass

    def _generate_docker_script(self):
        pass

    def get(self):
        self._pre_process()
        self._generate_docker_script()
        self._decide_docker_image()
        
        cmdline = "%s run %s %s bash -c '%s'" % (self.docker_binary, " ".join(self.docker_options), self.docker_image, self.docker_script)
        return cmdline

class DockerCMDLine_generator_PBS(DockerCMDLine_generator):
    def __init__(self):
        DockerCMDLine_generator.__init__(self, "")
        self._run_lines = []
        self._header_lines = [ "#!/bin/bash" ]
        self._pbs_options = {}

    def _pre_process(self):
        self._run_lines = []
        self._header_lines = [ "#!/bin/bash" ]
        self._pbs_options = {}
        
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

    def _decide_docker_image(self):
        queue = None
        if '-q' in self._pbs_options:
            queue = self._pbs_options['-q']
            
        # Now we could decide the container name according to the queue or the userinfo
            
        DockerCMDLine_generator._decide_docker_image(self)
    
    def _generate_docker_script(self):
        print "si"
        self.docker_script = "\n".join(self._run_lines)

#def get_pbs_options(header_script):
#    pbs_options = {}
#    for line in header_script:
#        line = line.rstrip("\n").strip()
#        if line[0:4] == "#PBS":
#            option = line[4:].strip().split(" ", 2)
#            while len(option) < 2:
#                option.append(None)
#            
#            flag, value = option
#            if flag is not None:
#                pbs_options[flag] = value
#                
#    return pbs_options
#
#def get_docker_image(username, group, groups, pbs_options, run_script):
#    docker_image = None
#    
#    queue = None
#    if '-q' in pbs_options:
#        queue = pbs_options['-q']
#    
#    if docker_image is None:
#        docker_image = DEFAULT_IMAGE
#        
#    return docker_image

if __name__ == '__main__':

    cmdline = DockerCMDLine_generator_PBS()
    print cmdline.get()
    #username, group, groups = get_user_info()
    #
    #docker_options = [ "--rm",
    #                  "-v /etc/passwd:/etc/passwd",     # This will allow to use the users in the host
    #                  "-v /etc/group:/etc/group",       # This will allow to use the groups in the host
    #                  "-u %s:%s" % (username, group),
    #                  ]
    #
    #run_script = [ ]
    #header_script = [ "#!/bin/bash" ]
    #
    #for line in sys.stdin:
    #    line = line.rstrip("\n")
    #    if line.strip()[0:4] == "#PBS":
    #        # This part will be used for the selection of resources
    #        header_script.append(line)
    #    else:
    #        run_script.append(line)
    #
    #print get_pbs_options(header_script)
    #
    #docker_image = get_docker_image(username, group, groups, get_pbs_options(header_script), run_script)           
    #docker_cmdline = "docker run %s %s bash -c '%s'" % (" ".join(docker_options), docker_image, "\n".join(run_script))
    #output_script = header_script + [ docker_cmdline ]
    #
    #print "\n".join(output_script)