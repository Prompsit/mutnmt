# MutNMT

"MultiTraiNMT - Machine Translation training for multilingual citizens" (2019-1-ES01-KA203-064245, 01/09/2019–31/08/2022)

## Deployment

MutNMT is distributed as a Docker container, based on the [NVIDIA CUDA container](https://github.com/NVIDIA/nvidia-docker/wiki/CUDA).

### Building MutNMT

You can build MutNMT with preloaded engines so that users have something to translate and inspect with. Before building the Docker image, 
include the engines you want to preload in the `app/preloaded` folder (create it if it does not exist).
Each engine must be stored in its own folder, and must have been trained with [JoeyNMT](https://github.com/joeynmt/joeynmt).
MutNMT will use the `model/train.log` to retrieve information about the engine, so make sure that file is available.

This is an example of an `app/preloaded` tree with one preloaded engine:

```
+ app/
|   + preloaded/
|   |   + transformer-en-es/
|   |   |    - best.ckpt
|   |   |    - config.yaml
|   |   |    - train.model
|   |   |    - train.vocab
|   |   |    - validations.txt
|   |   |    + model/
|   |   |    |    - train.log
|   |   |    |    + tensorboard/
```

Once you are ready, build MutNMT:

```
docker build -t mutnmt .
```

Then, launch the container. Since the NVIDIA CUDA container is **not** compatible with `docker-compose`, 
please launch MutNMT using the provided script.:

```
./run.sh cuda
```

This will setup MutNMT to run on port `5000`.

Manual installation is not described since it is not recommended. Anyway, [Dockerfile](Dockerfile) lists the needed packages and scripts.

## Hardware requirements

An NVIDIA graphics card is needed due to the fact that MutNMT is based on the [NVIDIA CUDA container](https://github.com/NVIDIA/nvidia-docker/wiki/CUDA).

## Multiple user account setup

Both installation procedures can provide multiple user accounts inside Mtradumatica based on the Google identity server through the OAUTH2 protocol. The procedure of setting such a server in the Google side is a bit complex and Google changes it from time to time, but it can be found [here]( https://developers.google.com/identity/protocols/OAuth2UserAgent). Although not official, a useful resource is [this video](https://www.youtube.com/watch?v=A_5zc3DYZfs).

From the process above, you will get at the end two strings, "client ID" and "client secret". You can edit the config.py file in the following way (alternatively, you can create a instance/config.py file with the following content):

```python
SECRET_KEY = 'put a random string here'
DEBUG      = False
ADMINS     = ['your.admin.account@gmail.com', 'your.second.admin.account@gmail.com']

USER_LOGIN_ENABLED          = True
USER_WHITELIST_ENABLED      = False
OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS
GOOGLE_OAUTH_CLIENT_ID      = 'xxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com'
GOOGLE_OAUTH_CLIENT_SECRET  = 'xxxxxxxxxxxxxxx'
USE_PROXY_FIX               = False
```

To specify admin accounts, please create a file in `app/lists` called `admin.list`, containing one administrator email per line. The admin accounts will allow you to use admin features as translator optimization or the remote Moses server. You can set as many as you want.

When user login is not enabled, a whitelist can be established to let the users in that list log in, but only them. This whitelist is only applied when `USER_LOGIN_ENABLED` is set to `False`. To specify a whitelist, create a file in `app/lists` called `white.list`, containing one user email per line.

Google Authentication may fail to work under some scenarios, for example behind an HTTP proxy. Set `USE_PROXY_FIX` to `True` in order to enable [Proxy Fix](https://werkzeug.palletsprojects.com/en/1.0.x/middleware/proxy_fix/) and make authentication work behind a proxy.
