import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

RANDOM_SEED = os.environ.get('RANDOM_SEED', '')


def get_server_html(base_url, index, *, load_all_routes=False):
    options = Options()
    options.add_argument('--headless=new')

    driver = webdriver.Chrome(options=options)

    path = index
    results = {}
    routes_to_load = None

    try:
        while True:
            print('[BeePy SSR] Processing page', path)
            driver.get(base_url + path)

            driver.execute_script((Path(__file__) / '../extra.js').resolve().read_text())
            driver.execute_script(
                '__update_config_obj(arguments[0])',
                {
                    'random_seed': RANDOM_SEED,
                    'server_side': 'server',
                },
            )
            driver.execute_script('window.dispatchEvent(new Event("beepy::server_side:load"))')
            WebDriverWait(driver, 2).until(EC.visibility_of_element_located((By.ID, 'beepy-loading')))
            WebDriverWait(driver, 25).until(EC.invisibility_of_element_located((By.ID, 'beepy-loading')))

            time.sleep(0.3)  # Need to finish rendering to have correct HTML

            driver.execute_script(
                '__add_meta_config_elements(arguments[0])',
                {
                    'random_seed': RANDOM_SEED,
                    'server_side': 'client',
                },
            )

            if routes_to_load is None:
                routes_to_load = set(driver.execute_script('return beepy.config._ssr_all_routes'))

            results[path] = driver.page_source

            driver.execute_script('document.documentElement.innerHTML = ""')

            if not load_all_routes:  # single page loading
                break

            if routes_left := (routes_to_load - set(results)):
                path = next(iter(routes_left))
            else:  # all routes are loaded
                break

        return results if load_all_routes else results[path]

    except Exception as e:
        print(e)
        raise
    finally:
        driver.quit()


def create_ssr_dist(root, base_url, index):
    dist = Path(root / 'dist')

    pages = get_server_html(base_url, index, load_all_routes=True)
    for path, page_source in pages.items():  # TODO: make get_server_html's generator version to write files immediately
        print('[BeePy SSR] Writing page', path)
        full_path = dist / path.lstrip('/')
        full_path.mkdir(parents=True, exist_ok=True)
        (full_path / 'index.html').write_text(page_source)
