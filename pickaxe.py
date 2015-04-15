#!/usr/bin/python
import collections
import datetime
import json
import numpy
import operator
import os
import re
import sys

pfx_pattern = re.compile('/([a-z_]+){locality#(\d+)/total}/(?:(?:(count|time)/)([a-z/_-]+)|([a-z/_-]+)/(?:(count|time))),([0-9]+),([0-9.]+),\[[a-z]+\],([0-9.\+e]+)(?:,\[([a-z]+)?\])?')
nodes_pattern = re.compile('([0-9]+) nodes')

base_path = './data'
#base_path = os.path.abspath(base_path)
fx_data = {}

# Parse HPX counter files
for file_name in os.listdir(base_path):
    print 'Reading', file_name
    if not file_name.endswith('.txt'):
        print 'Skipped...'
        continue
    path = os.path.join(base_path, file_name)

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
#with open(base_path + '/../all.json', 'w') as f:
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
    plot_data[counter_key] = {'max': {}, 'min': {}, 'mean': {}}
    for node_key, node_items in counter_items.iteritems(): # Node count
        first_item = node_items[0]
        if len(node_items) > 1:
            vals = map(operator.itemgetter('value'), node_items)
            plot_data[counter_key]['max'][node_key] = numpy.max(vals)
            plot_data[counter_key]['min'][node_key] = numpy.min(vals)
            plot_data[counter_key]['mean'][node_key] = numpy.mean(vals)
        else:
            plot_data[counter_key]['mean'][node_key] = first_item['value']

markdown = '---\n'
markdown += 'layout: post\n'
markdown += 'title:  "{0}-{1}"\n'.format('1d_stencil_8', '472bcca415')
markdown += 'date:   {:%y/%m/%d %H:%M:%S}\n'.format(datetime.datetime.now())
markdown += 'categories: agas stencil_8\n'
markdown += '---\n'
markdown += 'Generated with [pickaxe.py](http://parsa.github.io/pickaxe.py)\n\n'
markdown += '## Figures\n'

markdown_images = ''
markdown_links = ''

# Sort the dictionary
plot_data = collections.OrderedDict(sorted(plot_data.items()))

# Generate output files
for counter_name in plot_data: # Counter level
    # GNUPlot output
    script_gnuplot = os.path.abspath('{0}/../processed/{1}.gnuplot'.format(base_path, counter_name))
    image_gnuplot = os.path.abspath('{0}/../assets/{1}.png'.format(base_path, counter_name))

    # GNUPlot script
    cmd_gnuplot = ''
    cmd_gnuplot += 'set terminal png noenhanced font \'Arial,10\'\n'
    cmd_gnuplot += 'set output \'{0}\'\n'.format(image_gnuplot)
    # plot 'agas-increment_credit-time-mean.data' title 'Mean' with linespoints, 'agas-increment_credit-time-max.data' title 'Max' with linespoints, 'agas-increment_credit-time-min.data' title 'Min' with linespoints
    subplot = []
    for summary_name, summary_values in plot_data[counter_name].iteritems(): # Value Type
        plot_title = '{0}-{1}'.format(counter_name, summary_name)

        file_path = os.path.abspath('{0}/../processed/{1}.data'.format(base_path, plot_title))
        print 'Writing to', file_path
        with open(file_path, 'w') as f:
            f.write('\n# Curve 0, {0} points\n'.format(len(summary_values)))
            f.write('# Curve title "{0}"\n'.format(plot_title))
            f.write('# nodes, value\n')
            for key, value in summary_values.iteritems():
                f.write('{0} {1}\n'.format(key, value))
        subplot.append('\'{0}\' title \'{1}\' with linespoints'.format(file_path, summary_name))

    # Markdown links and images
    sane_counter_name =  ''.join(x for x in counter_name if x.isalnum())

    markdown_links += '- [{0}](#{1})\n'.format(counter_name, sane_counter_name)

    markdown_images += '### {0} {{#{1}}}\n'.format(counter_name, sane_counter_name)
    markdown_images += '[![{0}](/assets/{0}.png)](/assets/{0}.png "{0}.png")\n\n'.format(counter_name)
    markdown_images += '[Back to top](#figures)\n\n'
    # GNUPlot file
    cmd_gnuplot += 'set title \'{0}\'\n'.format(counter_name)
    cmd_gnuplot += 'set xlabel \'Nodes\'\n'
    cmd_gnuplot += 'set style line 102 lc rgb \'#d6d7d9\' lt 0 lw 1\n'
    cmd_gnuplot += 'set grid back ls 102\n'
    cmd_gnuplot += 'plot {0}\n'.format(', '.join(subplot))
    with open(script_gnuplot, 'w') as f:
        f.writelines(cmd_gnuplot)
    cmd = 'gnuplot {0}'.format(script_gnuplot)
    print 'Executing', cmd
    os.system(cmd)

markdown += markdown_links + '\n'
markdown += '***\n\n'
markdown += markdown_images

with open('./index.md', 'w') as m:
    m.write(markdown)
