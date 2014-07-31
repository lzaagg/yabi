import os
from lettuce import *
import lettuce_webdriver.webdriver


@step('I go to "(.*)"')
def our_goto(step, relative_url):
    """
    NB. This allows tests to run in different contexts ( locally, staging.)
    We delegate to the library supplied version of the step with the same pattern after fixing the path
    """
    absolute_url = world.site_url + relative_url
    lettuce_webdriver.webdriver.goto(step, absolute_url)


@step('I should see "(.*)"')
def eventually(step, expected_string):
    number_of_seconds_to_wait = getattr(world, "wait_seconds", 10)
    lettuce_webdriver.webdriver.should_see_in_seconds(step, expected_string, number_of_seconds_to_wait)


@step('I log in as "(.*)" with "(.*)" password')
def login_as_user(step, username, password):
    username_field = world.browser.find_element_by_xpath('.//input[@name="username"]')
    username_field.send_keys(username)
    password_field = world.browser.find_element_by_xpath('.//input[@name="password"]')
    password_field.send_keys(password)
    password_field.submit()


def get_site_url(app_name, default_url):
    """
    :return: http://example.com:8081
    """
    return os.environ.get('YABIURL', default_url)