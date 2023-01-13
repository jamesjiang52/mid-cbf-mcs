#
# Project makefile for ska-mid-cbf-mcs project. You should normally only need to modify
# DOCKER_REGISTRY_USER and PROJECT below.
#

#
# DOCKER_REGISTRY_HOST, DOCKER_REGISTRY_USER and PROJECT are combined to define
# the Docker tag for this project. The definition below overwrites
# DOCKER_REGISTRY_USER and PROJECT
#
#DOCKER_REGISTRY_USER:=ska-docker
PROJECT = ska-mid-cbf-mcs

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-cbf
SDP_KUBE_NAMESPACE ?= sdp #namespace to be used
DASHBOARD ?= webjive-dash.dump
DOMAIN ?= cluster.local

# HELM_RELEASE is the release that all Kubernetes resources will be labelled
# with
HELM_RELEASE ?= test

# HELM_CHART the chart name
HELM_CHART ?= ska-mid-cbf-umbrella

TANGO_DATABASE = tango-host-databaseds-from-makefile-$(HELM_RELEASE)
TANGO_HOST = $(TANGO_DATABASE):10000## TANGO_HOST is an input!

# Python variables
PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=./src:/app/src:/app/src/ska_mid_cbf_mcs KUBE_NAMESPACE=$(KUBE_NAMESPACE) HELM_RELEASE=$(RELEASE_NAME) TANGO_HOST=$(TANGO_HOST)

# Ignoring 501 which checks line length. There are over 500 failures for this in the code due to commenting. 
# Also ignoring 503 because operators can either be before or after line break(504). 
# We are choosing a standard to have it before the line break and therefore 503 will be ignored.
PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E501,F407,W503


# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
UMBRELLA_CHART_PATH ?= charts/ska-mid-cbf-umbrella/

K8S_CHARTS ?= ska-mid-cbf-umbrella ska-mid-cbf-mcs ska-mid-cbf-tmleafnode ## list of charts
K8S_UMBRELLA_CHART_PATH ?= ./charts/ska-mid-cbf-umbrella

PYTHON_TEST_FILE = 
PYTHON_VARS_AFTER_PYTEST = -c setup-unit-test.cfg

# Fixed variables
# Timeout for gitlab-runner when run locally
TIMEOUT = 86400
# Helm version
HELM_VERSION = v3.3.1
# kubectl version
KUBERNETES_VERSION = v1.19.2

# Docker, K8s and Gitlab CI variables
# gitlab-runner debug mode - turn on with non-empty value
RDEBUG ?=
# gitlab-runner executor - shell or docker
EXECUTOR ?= shell
# DOCKER_HOST connector to gitlab-runner - local domain socket for shell exec
DOCKER_HOST ?= unix:///var/run/docker.sock
# DOCKER_VOLUMES pass in local domain socket for DOCKER_HOST
DOCKER_VOLUMES ?= /var/run/docker.sock:/var/run/docker.sock
# registry credentials - user/pass/registry - set these in PrivateRules.mak
CAR_OCI_REGISTRY_USER_LOGIN ?=  ## registry credentials - user - set in PrivateRules.mak
CI_REGISTRY_PASS_LOGIN ?=  ## registry credentials - pass - set in PrivateRules.mak
CI_REGISTRY ?= gitlab.com/ska-telescope/ska-mid-cbf-mcs

CI_PROJECT_DIR ?= .

KUBE_CONFIG_BASE64 ?=  ## base64 encoded kubectl credentials for KUBECONFIG
KUBECONFIG ?= /etc/deploy/config ## KUBECONFIG location

ARTIFACTS_POD = $(shell kubectl -n $(KUBE_NAMESPACE) get pod --no-headers --selector=vol=artifacts-admin -o custom-columns=':metadata.name')

HOST_IP = $(shell ifconfig eno2 | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*')

XAUTHORITYx ?= ${XAUTHORITY}
THIS_HOST := $(shell ifconfig | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY := $(THIS_HOST):0

# define private overrides for above variables in here
-include PrivateRules.mak

# Test runner - run to completion job in K8s
# name of the pod running the k8s_tests
# TODO: test-makefile-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE) 
#		old name is 64 characters, too long for container name
TEST_RUNNER = test-runner-$(CI_JOB_ID)-$(KUBE_NAMESPACE)-$(HELM_RELEASE)

ifneq ($(strip $(CI_JOB_ID)),)
K8S_TEST_IMAGE_TO_TEST = $(CI_REGISTRY)/ska-telescope/ska-mid-cbf-mcs/ska-mid-cbf-mcs:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
K8S_CHART_PARAMS = --set global.minikube=false --set global.tango_host=$(TANGO_HOST) --set ska-mid-cbf-tmleafnode.midcbf.image.registry=$(CI_REGISTRY)/ska-telescope/ska-mid-cbf-mcs --set ska-mid-cbf-mcs.midcbf.image.registry=$(CI_REGISTRY)/ska-telescope/ska-mid-cbf-mcs --set ska-mid-cbf-mcs.midcbf.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
PYTHON_RUNNER = python3 -m
K8S_TEST_IMAGE_TO_TEST = artefact.skao.int/ska-mid-cbf-mcs:$(VERSION)
K8S_CHART_PARAMS = --set global.tango_host=$(TANGO_HOST) --set ska-mid-cbf-mcs.hostInfo.hostIP="$(HOST_IP)" --values taranta-values.yaml
endif

K8S_TEST_TEST_COMMAND ?= ls -lrt &&  $(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) \
                        pytest \
                        -c setup-integration-test.cfg \
                        | tee pytest.stdout; ## k8s-test test command to run in container

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#
include .make/release.mk
include .make/k8s.mk
include .make/make.mk
include .make/oci.mk
include .make/helm.mk
include .make/python.mk
include .make/docs.mk
#
# Defines a default make target so that help is printed if make is called
# without a target
#
.DEFAULT_GOAL := help

requirements: ## Install Dependencies
	python3 -m pip install -r requirements.txt

unit-test: ## Run simulation mode unit tests
	@mkdir -p build; \
	python3 -m pytest -c setup-unit-test.cfg


jive: ## configure TANGO_HOST to enable Jive
	@echo
	@echo 'With the deployment active, copy and run the following command to configure TANGO_HOST for local jive:'
	@echo
	export TANGO_HOST=$$(kubectl describe service -n $(KUBE_NAMESPACE) $(TANGO_DATABASE)-external | grep -i 'LoadBalancer Ingress' | awk '{print $$3}'):10000

update-db-port:  ## update Tango DB port so that the DB is accessible from the Talon boards on the Dell server
	kubectl -n ska-mid-cbf patch service/tango-host-databaseds-from-makefile-test --type='json' -p '[{"op":"replace","path":"/spec/ports/0/nodePort","value": 30176}]'

k8s-pre-test:
	@kubectl exec -n $(KUBE_NAMESPACE) $(ARTIFACTS_POD) -- mkdir -p /app/mnt/talondx-config
	@kubectl cp mnt/talondx-config/talondx-config.json $(KUBE_NAMESPACE)/$(ARTIFACTS_POD):/app/mnt/talondx-config/talondx-config.json

python-pre-lint:
	@pip3 install black isort flake8 pylint_junit typing_extensions

python-pre-build:
	@$(PYTHON_RUNNER) pip install sphinx==2.2

documentation:   ## ## Re-generate documentation
	cd docs && make clean && make html

help: ## show this help.
	@echo "make targets:"
	@echo "$(MAKEFILE_LIST)"
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ": .*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: all jive unit-test requirements test up down help k8s show lint logs describe mkcerts localip namespace delete_namespace ingress_check kubeconfig kubectl_dependencies helm_dependencies rk8s_test k8s_test rlint
