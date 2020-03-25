# MutNMT

"MultiTraiNMT - Machine Translation training for multilingual citizens" (2019-1-ES01-KA203-064245, 01/09/2019–31/08/2022)

## Deployment

MutNMT is distributed as a Docker container, based on the [NVIDIA CUDA container](https://github.com/NVIDIA/nvidia-docker/wiki/CUDA). Since the latter is **not** compatible with `docker-compose`, please launch MutNMT using the provided script:

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
OAUTHLIB_INSECURE_TRANSPORT = True # True also behind firewall,  False -> require HTTPS
GOOGLE_OAUTH_CLIENT_ID      = 'xxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxxx.apps.googleusercontent.com'
GOOGLE_OAUTH_CLIENT_SECRET  = 'xxxxxxxxxxxxxxx'
```
The admin accounts in ADMINS will allow you to use admin features as translator optimization or the remote Moses server. You can set as many as you want.
