from beepy import Style, state
from beepy.tags import html_tag, div, header, main, footer, nav, h1, ul, li, a, p, button, Head


Head.title = 'Техкоректор LaTeX'
Style.import_file('main.css')


def header_menu_item(href, link_title, *, title=''):
    return li(
        title,
        a(link_title, href=href),
        class_='header-menu__item',
    )


def hint(text):
    return p(text, class_='tex-input__hint', contenteditable=False)


class HighlightLaTeX(html_tag, name='latex'):
    children = [
        header(
            h1('Техкоректор'),
            nav(
                ul(
                    header_menu_item('/guide', 'Довідник'),
                    header_menu_item('https://t.me/texcorrector_bot', '@texcorrector_bot', title="Зворотній зв'язок: "),
                    class_='header-menu',
                )
            ),
        ),
        main(
            div(
                hint('Вставте статтю, написану в Теху.'),
                hint('Ще не написали?'),
                button('Вставити приклад', class_='tex-input__insert-example-button', contenteditable=False),
                class_='tex-input',
                contenteditable=True,
            ),
            div(
                # TBD
                id='explanation',
            )
        ),
        footer(
            p('Техкоректор допомагає науковцям писати охайні Латех-файли, вказуючи на типові помилки у верстці'),
            p(
                'Запрограмовано на ',
                a(
                    'BeePy',
                    class_='text-link',
                    href='https://beta.drukarnia.com.ua/articles/maibutnye-frontendu-paiton-VAVB2',
                ),
                class_='small',
            )
        ),
    ]
