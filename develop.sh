#!/bin/sh
#
# Script for dev, test and ci
#

: ${PROJECT_NAME:='yabi'}
. ./lib.sh

# break on error
set -e

ACTION="$1"

# build a docker image and start stack on staging using docker-compose
ci_docker_staging() {
    info 'ci docker staging'
    ssh ubuntu@staging.ccgapps.com.au << EOF
      mkdir -p ${PROJECT_NAME}/data
      chmod o+w ${PROJECT_NAME}/data
EOF

    scp docker-compose-*.yml ubuntu@staging.ccgapps.com.au:${PROJECT_NAME}/

    # TODO This doesn't actually do a whole lot, some tests should be run against the staging stack
    ssh ubuntu@staging.ccgapps.com.au << EOF
      cd ${PROJECT_NAME}
      docker-compose -f docker-compose-staging.yml stop
      docker-compose -f docker-compose-staging.yml kill
      docker-compose -f docker-compose-staging.yml rm --force -v
      docker-compose -f docker-compose-staging.yml up -d
EOF
}


docker_staging_lettuce() {
    _selenium_stack_up

    set -x
    set +e
    ( docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml rm --force || exit 0 )
    (${CMD_ENV}; docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml build)
    docker-compose --project-name ${PROJECT_NAME} -f docker-compose-staging-lettuce.yml up
    rval=$?
    set -e
    set +x

    _selenium_stack_down

    exit $rval
}


# lint using flake8
python_lint() {
    info "python lint"
    docker-compose -f docker-compose-build.yml run --rm lint flake8 yabi/yabi yabish/yabishell --exclude=migrations --ignore=E501 --count
    success "python lint"
}


# lint js, assumes closure compiler
js_lint() {
    info "js lint"
    JSFILES="yabi/yabi/yabifeapp/static/javascript/*.js yabi/yabi/yabifeapp/static/javascript/account/*.js"
    for JS in $JSFILES
    do
        docker-compose -f docker-compose-build.yml run lint gjslint --disable 0131 --max_line_length 100 --nojsdoc $JS
    done
    success "js lint"
}


echo ''
info "$0 $@"
docker_options
git_tag

case $ACTION in
pythonlint)
    python_lint
    ;;
jslint)
    js_lint
    ;;
dev)
    start_dev
    ;;
dev_build)
    create_base_image
    create_build_image
    create_dev_image
    ;;
django-admin)
    shift
    django_admin $@
    ;;
check_migrations)
    check_migrations
    ;;
releasetarball)
    create_release_tarball
    ;;
prod)
    start_prod
    ;;
prod_build)
    create_base_image
    create_build_image
    create_release_tarball
    create_prod_image
    ;;
baseimage)
    create_base_image
    ;;
buildimage)
    create_build_image
    ;;
prodimage)
    create_prod_image
    ;;
devimage)
    create_dev_image
    ;;
publish_docker_image)
    publish_docker_image
    ;;
runtests)
    create_base_image
    create_build_image
    create_dev_image
    run_unit_tests
    ;;
start_test_stack)
    start_test_stack
    ;;
start_seleniumhub)
    start_seleniumhub
    ;;
docker_warm_cache)
    docker_warm_cache
    ;;
ci_docker_login)
    ci_docker_login
    ;;
ci_docker_staging)
    _ci_ssh_agent
    ci_docker_staging
    ;;
docker_staging_lettuce)
    docker_staging_lettuce
    ;;
dev_lettuce)
    dev_lettuce
    ;;
lettuce)
    dev_lettuce
    ;;
prod_lettuce)
    prod_lettuce
    ;;
*)
    usage
    ;;
esac
