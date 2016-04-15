# Docker4HPC
The system administrator of a cluster has a lot of requirements to meet from the applications of the users. There are a lot of libraries that the users require, applications, etc. even different versions of the same library. That means that it is needed to create a complex installation of the system, and environment variables (e.g. LD_LIBRARY_PATH). Moreover, the cluster has a specific installation, with an operating system, but each user develop their apps under different versions or flavours of a OS. Even the users may need to use a legacy applications that runs on a specific flavour and version of Linux, but the cluster has another newer version (e.g. an application that runs under CentOS 6.6 but not under CentOS 7).

Docker4HPC tries to get profit from the Docker containers, to containerize the runs of the applications that are submited to the queue. Docker4HPC intercept the job in the queue and creates the proper ```docker run``` call to run the submitted script or application inside a container in the internal node instead of running the script directly on the bare metal.

## Requirements
You simply have to install python 2.7 in the front-end, and docker in the internal nodes.

## How it works
The Torque version intercepts the submitted script prior to release to the torque-server, and inspects it to create a ```docker run``` call that will run the script. The selection of the nodes is kept (e.g. using #PBS decorators). It is possible to customize the docker image to be used depending on the main application ran in the script, the queue, the user or set a default docker image.

## Any requirement for the docker images?
Yes, you MUST install the applications that are allowed to be ran inside the docker images. But you only need to install these applications that are related to the specific container (e.g. if you have a specific container for a specific application, you need to install the applications and their requirements inside the docker image).

## How to install

The current version of Docker4HPC is working for _Torque_, but we are in active development of versions for other batch systems.

### Torque

In the front-end
1. Get Docker4HPC from its official repository
```bash
$ git clone https://github.com/grycap/docker4hpc
```
2. Put the docker4hpc.py application in a folder that is accesible by the users 
```bash
$ mv docker4hpc /opt
```
3. Modify the file /var/spool/torque.cfg and add the following line
```bash
SUBMITFILTER /opt/docker4hpc/docker4hpc.py
```
4. Create a configuration file from the example and modify it to customize to be used for your applications, users, queues and your deployment
```bash
cp /opt/docker4hpc/etc/docker4hpc.cfg-example /etc/docker4hpc.cfg
```

### Optional steps
In the configuration file you need to set the container images that will be used to run the jobs. The container images must be accesible from the internal nodes (these images will be retrieved by issuing a ```docker pull``` command). Take into account that you can use the _dockerhub.io_ repository, but it is also possible to set your private repository (e.g. in the front-end) and use it. Please refer to the docker documentation to create your private repository or open an issue and we'll try to explain.

## Testing prior to install
You can test ```Docker4HPC``` for Torque under a virtual environment, using [ec4docker](https://github.com/grycap/ec4docker) and the information under the _devel-env_ folder.

1. Install ```ec4docker``` and get the ec4docker command in the path
2. Generate the docker images in the front-end:
```bash
docker build -t ec4docker-s:frontend -f /path/to/ec4docker/frontend/Dockerfile.static /path/to/ec4docker/frontend
docker build -t docker4hpc:frontend -f /path/to/ec4docker/frontend/Dockerfile.torque-s /path/to/ec4docker/frontend
docker build -t ec4docker:wn -f /path/to/ec4docker/wn/Dockerfile.wn /path/to/ec4docker/wn
docker build -t ec4docker-torque:wn -f /path/to/ec4docker/wn/Dockerfile.torque /path/to/ec4docker/wn
docker build -t docker4hpc:wn -f /opt/docker4hpc/devel-env/Dockerfile.docker4hpc.wn /opt/docker4hpc/devel-env/
```
3. Launch the virtual cluster
```bash
ec4docker -f /opt/docker4hpc/devel-env/ec4docker-torque.config
```
4. Enter in the front-end and configure docker4hpc according to the instructions above.

