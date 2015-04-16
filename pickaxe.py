#!/usr/bin/python
import collections
import datetime
import json
import numpy
import operator
import os
import re
import sys

# Basic Configuration
index_generator = 'jekyll'
index_file = 'index.md'
asset_prefix = '/assets/2015-04-15-1d_stencil_8-472bcca415-0/'
app_name = '1d_stencil_8'
changeset = '472bcca415'
pickaxe_url = 'http://parsa.github.io/pickaxe.py'
dirs = {
    'data': './data',
    'images': './assets',
    'points': './processed',
    'scripts': './processed'
}

pfx_pattern = re.compile('/([a-z_]+){locality#(\d+)/total}/(?:(?:(count|time)/)([a-z/_-]+)|([a-z/_-]+)/(?:(count|time))),([0-9]+),([0-9.]+),\[[a-z]+\],([0-9.\+e]+)(?:,\[([a-z]+)?\])?')
nodes_pattern = re.compile('([0-9]+) nodes')

fx_data = {}

index_template = {
    'html': {
        'intro': '<html>\n'
                 '<head><title>{app_name}-{changeset}</title></head>\n'
                 '<body>\n'
                 '<h1><a id="figures">{app_name}-{changeset}</a></h1>\n'
                 '<p>Date: {timestamp:%y/%m/%d %H:%M:%S}</p>\n'
                 '<p>Generated with <a href="{pickaxe_url}">pickaxe.py</a></p>\n'
                 '<ul>\n',
        'links': '<li><a href=#{sane_counter_name}>{counter_name}</a></li>\n',
        'images': '<h3 id="{sane_counter_name}">{counter_name}</h3>\n'
                  '<a href="{asset_prefix}{counter_name}.png" title={counter_name}.png><img src="{asset_prefix}{counter_name}.png" alt="{counter_name}"/></a>\n'
                  '<p><a href=#figures>Back to top</a></p>\n\n',
        'mid': '</ul>\n\n<hr />\n\n',
        'footer': '</body>\n'
                  '</html>'
    },
    'markdown': {
        'intro': '# {app_name}-{changeset}\n'
                 'Date: {timestamp:%y/%m/%d %H:%M:%S}\n'
                 'Generated with [pickaxe.py]({pickaxe_url})\n\n'
                 '## Figures\n', # format: app_name=app_name, changeset=changeset, timestamp=datetime.datetime.now()
         'links': '- [{counter_name}](#{sane_counter_name})\n', # format: counter_name='', sane_counter_name=''
         'images': '### {counter_name} {{#{sane_counter_name}}}\n'
                   '[![{counter_name}]({asset_prefix}{counter_name}.png)]({asset_prefix}{counter_name}.png "{counter_name}.png")\n\n'
                   '[Back to top](#figures)\n\n', # format: counter_name='', sane_counter_name='',
         'mid': '\n***\n\n',
         'footer': ''
    },
    'jekyll': {
        'intro': '---\n'
                 'layout: post\n'
                 'title:  "{app_name}-{changeset}"\n'
                 'date:   {timestamp:%y/%m/%d %H:%M:%S}\n'
                 'categories: agas {app_name}\n'
                 '---\n'
                 'Generated with [pickaxe.py]({pickaxe_url})\n\n'
                 '## Figures\n', # format: app_name=app_name, changeset=changeset, timestamp=datetime.datetime.now()
         'links': '- [{counter_name}](#{sane_counter_name})\n', # format: counter_name='', sane_counter_name=''
         'images': '### {counter_name} {{#{sane_counter_name}}}\n'
                   '[![{counter_name}]({asset_prefix}{counter_name}.png)]({asset_prefix}{counter_name}.png "{counter_name}.png")\n\n'
                   '[Back to top](#figures)\n\n', # format: counter_name='', sane_counter_name='',
         'mid': '\n***\n\n',
         'footer': ''
    }
}

gnuplot_template = {
    'main':
        'set terminal png noenhanced font \'Arial,10\'\n'
        'set output \'{image_gnuplot}\'\n' # format: image_gnuplot
        'set title \'{counter_name}\'\n' # format: counter_name
        'set title \'{counter_name}\'\n' # format: counter_name
        'set xlabel \'Nodes\'\n'
        'set ylabel \'{metric}\'\n' # format: plot_data[counter_name]['metric']
        'set style line 102 lc rgb \'#d6d7d9\' lt 0 lw 1\n'
        'set grid back ls 102\n'
        'plot {subplots}\n', # format: ', '.join(subplot)
    'subplot': '\'{file_path}\' title \'{summary_name}\' with linespoints' #format: file_path, summary_name
}

# Parse HPX counter files
for file_name in os.listdir(dirs['data']):
    print 'Reading', file_name
    if not file_name.endswith('.txt'):
        print 'Skipped...'
        continue
    path = os.path.join(dirs['data'], file_name)

    with open(path) as pfx_data_file:
        no_nodes = 0 # Number of nodes
        for line in pfx_data_file:
            m = nodes_pattern.match(line)
            if m:
                no_nodes = int(m.group(1))

            m = pfx_pattern.match(line)
            if m:
                # Put the counters in a dictionary
                if m.group(3) != None:
                    entity = {
                        'cat': m.group(1),
                        'name': m.group(4).replace('/', '.'),
                        'type': m.group(3),
                        'locality': int(m.group(2)),
                        'value': float(m.group(9)),
                        'metric': m.group(10),
                        'timestamp': m.group(8),
                        'seqno': int(m.group(7))
                    }
                else:
                    entity = {
                        'cat': m.group(1),
                        'name': m.group(5).replace('/', '.'),
                        'type': m.group(6),
                        'locality': int(m.group(2)),
                        'value': float(m.group(9)),
                        'metric': m.group(10),
                        'timestamp': m.group(8),
                        'seqno': int(m.group(7))
                    }

                # Construct dictionary keyname
                keyname = '{0}-{1}-{2}'.format(entity['cat'], entity['name'], entity['type'])
                if fx_data.has_key(keyname):
                    if fx_data[keyname].has_key(no_nodes):
                        fx_data[keyname][no_nodes].append(entity)
                    else:
                        fx_data[keyname][no_nodes] = [entity]
                else:
                    fx_data[keyname] = {}
                    fx_data[keyname][no_nodes] = [entity]

    
## HACK: Dump all to json
#with open(dirs['index'] + '/../all.json', 'w') as f:
#    f.writelines(json.dumps(fx_data, sort_keys=True, indent=4, separators=(',', ': ')))

## HACK: Debug
#for i, vi in fx_data.iteritems():
#    print '====================\n' + i + ':\n===================='
#    for j, vj in vi.iteritems():
#        print '--------------------\n' + str(j) + ':\n--------------------'
#        print len(vj), vj

# Calculate statistics
plot_data = {}
for counter_key, counter_items in fx_data.iteritems(): # Counter name
    plot_data[counter_key] = {'stats': {'max': {}, 'min': {}, 'mean': {}, 'value': {}}, 'cat': '', 'name': '', 'type': '', 'metric': 'Count'}
    for node_key, node_items in counter_items.iteritems(): # Node count
        first_item = node_items[0]
        plot_data[counter_key]['cat'] = first_item['cat']
        plot_data[counter_key]['name'] = first_item['name']
        plot_data[counter_key]['type'] = first_item['type']
        if first_item['metric']:
            plot_data[counter_key]['metric'] = first_item['metric']

        if len(node_items) > 1:
            vals = map(operator.itemgetter('value'), node_items)
            plot_data[counter_key]['stats']['max'][node_key] = numpy.max(vals)
            plot_data[counter_key]['stats']['min'][node_key] = numpy.min(vals)
            plot_data[counter_key]['stats']['mean'][node_key] = numpy.mean(vals)
        else:
            plot_data[counter_key]['stats']['value'][node_key] = first_item['value']

index_output = index_template[index_generator]['intro'].format(app_name=app_name, changeset=changeset, timestamp=datetime.datetime.now(), pickaxe_url=pickaxe_url)

index_images = ''
index_links = ''

# Sort the dictionary
plot_data = collections.OrderedDict(sorted(plot_data.items()))

# Generate output files
for counter_name in plot_data: # Counter level
    # GNUPlot output
    script_gnuplot = os.path.abspath('{0}/{1}.gnuplot'.format(dirs['scripts'], counter_name))
    image_gnuplot = os.path.abspath('{0}//{1}.png'.format(dirs['images'], counter_name))

    subplot = []
    for summary_name, summary_values in plot_data[counter_name]['stats'].iteritems(): # Value Type
        if len(summary_values) == 0:
            continue

        plot_title = '{0}-{1}'.format(counter_name, summary_name)

        file_path = os.path.abspath('{0}/{1}.data'.format(dirs['points'], plot_title))
        print 'Writing to', file_path
        with open(file_path, 'w') as f:
            f.write('\n# Curve 0, {0} points\n'.format(len(summary_values)))
            f.write('# Curve title "{0}"\n'.format(plot_title))
            f.write('# nodes, value\n')
            for key, value in summary_values.iteritems():
                f.write('{0} {1}\n'.format(key, value))
        subplot.append(gnuplot_template['subplot'].format(file_path=file_path, summary_name=summary_name))

    # Markdown links and images
    sane_counter_name =  ''.join(x for x in counter_name if x.isalnum())

    index_links += index_template[index_generator]['links'].format(counter_name=counter_name, sane_counter_name=sane_counter_name)

    index_images += index_template[index_generator]['images'].format(counter_name=counter_name, sane_counter_name=sane_counter_name, asset_prefix=asset_prefix)

    # GNUPlot script
    # plot 'agas-increment_credit-time-mean.data' title 'Mean' with linespoints, 'agas-increment_credit-time-max.data' title 'Max' with linespoints, 'agas-increment_credit-time-min.data' title 'Min' with linespoints
    cmd_gnuplot = gnuplot_template['main'].format(image_gnuplot=image_gnuplot, counter_name=counter_name, metric = plot_data[counter_name]['metric'], subplots=', '.join(subplot))
    with open(script_gnuplot, 'w') as f:
        f.writelines(cmd_gnuplot)
    cmd = 'gnuplot {0}'.format(script_gnuplot)
    print 'Executing', cmd
    os.system(cmd)

index_output += index_links
index_output += index_template[index_generator]['mid']
index_output += index_images
index_output += index_template[index_generator]['footer']

with open(index_file, 'w') as m:
    m.write(index_output)

