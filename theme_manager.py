import streamlit as st
import plotly.graph_objects as go


def init_theme_manager():
    """
    Função mantida para compatibilidade com o código existente.
    Não faz mais nada, pois o tema agora é controlado pelo Streamlit.
    """
    pass


def toggle_theme():
    """
    Função mantida para compatibilidade com o código existente.
    Não faz mais nada, pois o tema agora é controlado pelo Streamlit.
    """
    pass


def apply_theme():
    """
    Função mantida para compatibilidade com o código existente.
    Não faz mais nada, pois o tema agora é controlado pelo Streamlit.
    """
    pass


def theme_config_section():
    """
    Função mantida para compatibilidade com o código existente.
    Agora exibe uma mensagem informativa sobre como alterar o tema.
    """
    pass


def get_theme_colors():
    """
    Retorna um dicionário de cores baseado no tema atual do Streamlit.
    """
    try:
        # Verifica o tema diretamente
        is_dark_theme = st.get_option("theme.base") == "dark"
    except Exception as e:
        # Fallback 1: Verifica a cor de fundo
        try:
            background_color = st.get_option("theme.backgroundColor")
            is_dark_theme = background_color.lower() in ["#0e1117", "#1e1e1e", "black", "#15191c", "#1a1d23"]
        except Exception as e:
            # Fallback 2: Verifica a cor do texto
            try:
                text_color = st.get_option("theme.textColor")
                is_dark_theme = text_color.lower() in ["#ffffff", "#fafafa", "white", "#d3d3d3", "#e5e5e5"]
            except Exception as e:
                # Fallback 3: Usa tema claro como padrão
                is_dark_theme = False

    if is_dark_theme:
        return {
            'background': '#0e1117',
            'paper_bgcolor': '#0e1117',
            'plot_bgcolor': '#0e1117',
            'font_color': '#fafafa',
            'grid_color': 'rgba(255, 255, 255, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Plasma',
            'accent_color': '#64b5f6',
            'success_color': '#66bb6a',
            'warning_color': '#ffb74d',
            'error_color': '#e57373',
            'neutral_color': '#9e9e9e'
        }
    else:
        return {
            'background': 'white',
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'white',
            'font_color': '#262730',
            'grid_color': 'rgba(0, 0, 0, 0.1)',
            'revenue_color': '#4CAF50',
            'expense_color': '#EF5350',
            'investment_color': '#42A5F5',
            'colorscale': 'Viridis',
            'accent_color': '#1e88e5',
            'success_color': '#4caf50',
            'warning_color': '#ff9800',
            'error_color': '#f44336',
            'neutral_color': '#757575'
        }


def apply_theme_to_plotly_chart(fig):
    """
    Aplica o tema atual a um gráfico Plotly existente.
    """
    theme_colors = get_theme_colors()
    bg_color = theme_colors['plot_bgcolor']
    text_color = theme_colors['font_color']
    grid_color = theme_colors['grid_color']

    fig.update_layout(
        template=None,
        paper_bgcolor=bg_color,
        plot_bgcolor=bg_color,
        font=dict(color=text_color),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            gridcolor=grid_color,
            tickfont=dict(color=text_color),
            title_font=dict(color=text_color)
        ),
        yaxis=dict(
            gridcolor=grid_color,
            tickfont=dict(color=text_color),
            title_font=dict(color=text_color)
        ),
        legend=dict(font=dict(color=text_color))
    )

    if hasattr(fig, 'data'):
        for trace in fig.data:
            if hasattr(trace, 'textfont') and trace.textfont:
                trace.textfont.color = text_color
            if hasattr(trace, 'legendgrouptitle') and trace.legendgrouptitle:
                if hasattr(trace.legendgrouptitle, 'font'):
                    trace.legendgrouptitle.font.color = text_color
                else:
                    trace.legendgrouptitle.font = dict(color=text_color)

    if hasattr(fig.layout, 'annotations'):
        for annotation in fig.layout.annotations:
            if hasattr(annotation, 'font') and annotation.font:
                annotation.font.color = text_color

    return fig


def create_pie_chart(labels, values, title=""):
    """
    Cria um gráfico de pizza com o tema atual.
    Compatível com tema escuro e claro do Streamlit.
    """
    theme_colors = get_theme_colors()

    colors = (
        ['#0d0887', '#46039f', '#7201a8', '#9c179e', '#bd3786',
         '#d8576b', '#ed7953', '#fb9f3a', '#fdca26', '#f0f921']
        if theme_colors['colorscale'] == 'Plasma' else
        ['#440154', '#482878', '#3e4989', '#31688e', '#26828e',
         '#1f9e89', '#35b779', '#6ece58', '#b5de2b', '#fde725']
    )

    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            textinfo='percent+label',
            textposition='inside',
            textfont=dict(color=theme_colors['font_color']),
            insidetextfont=dict(color=theme_colors['font_color']),
            hoverinfo='label+percent+value',
            hole=0.4
        )
    ])

    fig.update_layout(
        title=title,
        title_font_color=theme_colors['font_color'],
        font=dict(color=theme_colors['font_color']),
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['plot_bgcolor'],
        legend=dict(font=dict(color=theme_colors['font_color'])),
        margin=dict(l=10, r=10, t=30, b=10)
    )

    return fig


def create_bar_chart(x, y, title=""):
    """
    Cria um gráfico de barras com o tema atual.
    """
    theme_colors = get_theme_colors()

    fig = go.Figure(data=[
        go.Bar(
            x=x,
            y=y,
            marker_color=theme_colors['accent_color'],
            hoverinfo='x+y',
            texttemplate='%{y:.2f}',
            textposition='auto',
            textfont=dict(color=theme_colors['font_color'])
        )
    ])

    fig.update_layout(
        title=title,
        title_font_color=theme_colors['font_color'],
        font_color=theme_colors['font_color'],
        paper_bgcolor=theme_colors['paper_bgcolor'],
        plot_bgcolor=theme_colors['plot_bgcolor'],
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color']),
            title_font=dict(color=theme_colors['font_color'])
        ),
        yaxis=dict(
            gridcolor=theme_colors['grid_color'],
            tickfont=dict(color=theme_colors['font_color']),
            title_font=dict(color=theme_colors['font_color'])
        )
    )

    return fig


def style_dataframe(df):
    """
    Estiliza um DataFrame pandas para se adequar ao tema atual.
    Retorna um estilo aplicado ao DataFrame.
    """
    theme_colors = get_theme_colors()

    return df.style.set_properties(**{
        'background-color': theme_colors['paper_bgcolor'],
        'color': theme_colors['font_color'],
        'border': f'1px solid {theme_colors["grid_color"]}'
    }).set_table_styles([
        {'selector': 'th', 'props': [
            ('background-color', theme_colors['plot_bgcolor']),
            ('color', theme_colors['font_color']),
            ('border', f'1px solid {theme_colors["grid_color"]}'),
            ('padding', '8px')
        ]},
        {'selector': 'tr:hover td', 'props': [
            ('background-color', 'rgba(66, 165, 245, 0.1)')
        ]}
    ])
