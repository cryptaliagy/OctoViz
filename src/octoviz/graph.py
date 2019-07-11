import re, itertools
from bokeh.plotting import figure, ColumnDataSource
from bokeh.palettes import Category10 as palette

def data_to_graph_params(data, width, name_map, is_datetime, round_to, skip_last=False):
    def colors():
        yield from itertools.cycle(palette[10])
        
    color = colors()
    line_result = {}
    bar_result = {}
    end_index = -1 if skip_last else None
    for param in data:
        match = re.match('(1?[0-9]?[0-9])th', param)
        x = []
        y = []
        for key in sorted(data[param].keys())[:end_index]:
            x.append(key)
            y.append(data[param][key])
        if match:
            line_result[param] = {
                'legend': "{}%-tile time".format(match[1]),
                'color': next(color),
                'x': x,
                'y': y,
                'time': y
            }
            if is_datetime:
                line_result[param]['date'] = list(map(lambda x: x.strftime('%b %d %y'), x))
            else:
                line_result[param]['lines'] = list(map(lambda x: '%d-%d' % (x, x+round_to-1), x))
        else:
            bar_result[param] = {
                'width': width,
                'legend': name_map[param],
                'x': x,
                'top': y,
                'fill_color': next(color),
            }
    return line_result, bar_result


def graph(line_data, bar_data, repository_name, frame, grouped, x_range=None, y_range=None, bar_y_range=None, is_datetime=True, custom_title = ""):
    axis_type = 'datetime' if is_datetime else 'linear'
    time = frame if is_datetime else 'lines changed -'
    if custom_title:
        title = custom_title
    else:
        title = "Pull Request Data for %s, Aggregated by %s %s" % (repository_name.capitalize(), time.capitalize(), grouped.capitalize())
    if is_datetime:
        tooltips = [
            ('Date', '@date'),
            ('Days to close', '@time')
        ]
    else:
        tooltips = [
            ('Lines', '@lines'),
            ('Days to close', '@time')
        ]
    line_chart = figure(
        title=title,
        x_axis_label="Date" if is_datetime else "Number of lines", 
        y_axis_label='Time to close PR (days)',
        x_axis_type=axis_type,
        tooltips=tooltips)

    if x_range is not None:
        line_chart.x_range = x_range
    if y_range is not None:
        line_chart.y_range = y_range

    bar_tooltip = [('Pull Requests', '@top')]

    bar_chart = figure(
        title=title, 
        x_axis_label='Date' if is_datetime else 'Number of Lines',
        x_range=line_chart.x_range,
        x_axis_type=axis_type,
        tooltips=bar_tooltip)
    
    if bar_y_range is not None:
        bar_chart.y_range = bar_y_range
    
    for key in line_data.keys():
        data_dict = dict(
            x=line_data[key]['x'],
            y=line_data[key]['y'],
            time=line_data[key]['time']
        )
        if is_datetime:
            data_dict['date'] = line_data[key]['date']
        else:
            data_dict['lines'] = line_data[key]['lines']

        source = ColumnDataSource(data=data_dict)
        line_chart.line('x', 'y', line_width=2, source=source, legend=line_data[key]['legend'], line_color=line_data[key]['color'])
        line_chart.circle('x', 'y', size=5, source=source, legend=line_data[key]['legend'], color=line_data[key]['color'])
    
    for key in bar_data.keys():
        bar_chart.vbar(**bar_data[key])
    
    line_chart.legend.click_policy = 'hide'

    return [line_chart, bar_chart]