import io
import base64

from beepy.tags import img


def get_plot_img(figure, **kwargs):
    buf = io.BytesIO()
    figure.savefig(buf, format='png')
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode('utf-8')
    return img(src=f'data:image/png;charset=utf-8;base64,{data}', **kwargs)
