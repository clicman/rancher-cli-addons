# Rancher Client Addons
In reaction to [rancher #4570](https://github.com/rancher/rancher/issues/4570) 

##Features
* Create/Upgrade/Remove stack
* Add/Remove load balancer's service links
* Add/Remove domains at [Yandex DNS service](https://pdd.yandex.ru)

##Requirements:
* Python>=2.7
* python-requests
* python-yaml

##Usage
###rancher-cli
* Create/Upgrade/Remove Rancher stacks
* Add/Remove load balancer's service links

Possible environment variables (Optional, also can be set as command line arguments):
```
RANCHER_API_URL='https://rancher.yourdomain.com'
RANCHER_API_KEY=228E5F4B58373A000F30
RANCHER_API_SECRET=LN3NNrPG28Deb954d4BusosAASsmDHoFMkbiT8Vd
RANCHER_LB_ID=1s121 #HTTP LB service id. You can find it on its url path
RANCHER_LB_TCP_ID=1s121 #TCP LB service id. You can find it on its url path
RANCHER_LB_IP=10.10.10.11 #HTTP LB ip
RANCHER_LB_TCP_IP=10.10.10.12 # TCP LB ip
```

Examples:
```
#Create stack. If stack already exists it will upgraded.
./rancher-cli.py --action=create-stack --stackName=${STACK_NAME} \
--dockerCompose=docker-compose.yml --rancherCompose=rancher-compose.yml

#Add load balancer target, so service will be available via http
#${HTTP_SERVICE_NAME} - is a service name from dockder-compose.yml
#${STACK_NAME} - stack name
#${MY_DOMAIN} - domain where it will registered
#NOTE! host must always be builded as ${SERVICE_NAME}.${STACK_NAME}.${MY_DOMAIN}!!!
./rancher-cli.py --action=add-link --externalPort=80 --host=${HTTP_SERVICE_NAME}.${STACK_NAME}.${MY_DOMAIN} \
--internalPort=8080

#If you want to add tcp service link which will be externally accesible you should set '--externalPort' 
#parameter (and it should be registered on load balancer as tcp port
#${HTTP_SERVICE_NAME} - is a service name from dockder-compose.yml
#${STACK_NAME} - stack name
#${MY_DOMAIN} - domain where it will registered
#NOTE! host must always be builded as ${SERVICE_NAME}.${STACK_NAME}.${MY_DOMAIN}!!!
./rancher-cli.py --action=add-link --externalPort=`./rancher-cli.py --action=get-port \
--loadBalancerId=${RANCHER_LB_TCP_ID}` --host=${TCP_SERVICE_NAME}.${STACK_NAME}.${MY_DOMAIN}
--internalPort=${DB_MONGO_PORT} --loadBalancerId=${RANCHER_LB_TCP_ID}

#Remove stack
rancher-cli.py --action=remove-stack --stackName=${STACK_NAME}
```

###yandex-domain-manager
* Add/Remove domains at [Yandex DNS service](https://pdd.yandex.ru)

Possible environment variables (Optional, also can be set as command line arguments):
```
PDD_TOKEN= #pdd.yandex.ru api token
```

Examples:
```
./yandex-domain-manager.py add full.domain.name --ip=10.10.10.12 --ttl=360 #ttl is optional, default value is 360
./yandex-domain-manager.py remove full.domain.name
```


###yaml-modifier
* Handy utility to modify docker-compose/rancher-compose or other YAML files on fly

Examples:
```
yaml-modifier.py docker-compose.yml ${MAIN_SERVICE_NAME}.environment.COMMIT_HASH ${sourceCommitHash}
yaml-modifier.py docker-compose.yml api.environment.DB_POSTGRES_HOST ${DB_POSTGRES_HOST}
yaml-modifier.py docker-compose.yml api.environment.DB_POSTGRES_PORT ${DB_POSTGRES_PORT}
yaml-modifier.py docker-compose.yml api.environment.DB_POSTGRES_DB ${DB_POSTGRES_DB}
yaml-modifier.py docker-compose.yml api.environment.DB_POSTGRES_USER ${DB_POSTGRES_USER}
yaml-modifier.py docker-compose.yml api.environment.DB_POSTGRES_PASSWORD ${DB_POSTGRES_PASSWORD}
yaml-modifier.py docker-compose.yml site.environment.API_URL "http://api.${SERVICE_DOMAIN}"
```

