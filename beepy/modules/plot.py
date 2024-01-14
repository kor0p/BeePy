import base64
import io


def get_plot_img_src(figure):
    buf = io.BytesIO()
    figure.savefig(buf, format='png')
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode('utf-8')
    return f'data:image/png;charset=utf-8;base64,{data}'
