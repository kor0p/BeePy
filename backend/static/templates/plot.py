import matplotlib.pyplot as plt
import numpy as np

from beepy import Tag, import_css
from beepy.modules.plot import get_plot_img_src
from beepy.tags import button, img

import_css('styles/plot.css')

rng = np.random.default_rng()


def create_plot():
    plt.clf()
    # example from https://matplotlib.org/stable/tutorials/introductory/pyplot.html
    data = {'a': np.arange(50), 'c': rng.integers(0, 50, 50), 'd': rng.standard_normal(50)}
    data['b'] = data['a'] + 10 * rng.standard_normal(50)
    data['d'] = np.abs(data['d']) * 100

    plt.scatter('a', 'b', c='c', s='d', data=data)
    plt.xlabel('entry a')
    plt.ylabel('entry b')

    return plt


class App(Tag, name='app'):
    children = [
        reload_btn := button('Reload', class_='reload'),
        plot := img(class_='plot'),
    ]

    def mount(self):
        self.reload_plot()

    @reload_btn.on('click')
    def reload_plot(self):
        self.plot.src = get_plot_img_src(create_plot())
