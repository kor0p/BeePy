import matplotlib.pyplot as plt
import numpy as np

from pyweb import Tag, Style
from pyweb.children import Children
from pyweb.tags import button
from pyweb.plot import get_plot_img


Style.import_file('styles/plot.css')


def create_plot():
    plt.clf()
    # example from https://matplotlib.org/stable/tutorials/introductory/pyplot.html
    data = {'a': np.arange(50),
            'c': np.random.randint(0, 50, 50),
            'd': np.random.randn(50)}
    data['b'] = data['a'] + 10 * np.random.randn(50)
    data['d'] = np.abs(data['d']) * 100

    plt.scatter('a', 'b', c='c', s='d', data=data)
    plt.xlabel('entry a')
    plt.ylabel('entry b')

    # plt.show()
    return get_plot_img(plt, class_='plot')


class App(Tag, name='app'):
    reload_btn = button('Reload', class_='reload')
    plot = Children([])

    children = [
        reload_btn,
        plot,
    ]

    def mount(self):
        self.reload_plot()

    @reload_btn.on('click')
    def reload_plot(self, event=None):
        self.plot[:] = [create_plot()]
