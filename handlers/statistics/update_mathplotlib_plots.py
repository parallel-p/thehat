__author__ = 'ivan'


from google.appengine.ext import ndb
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
import StringIO

from google.appengine.api import taskqueue

import logging


class Plot(ndb.Model):

    plot = ndb.BlobProperty(indexed=False)


class runUpdateAll(ServiceRequestHandler):
    urls = [
            '/internal/update_heatmap/task_queue',
            '/internal/update_heatmap/task_queue',
            '/internal/update_heatmap/task_queue',
            '/internal/update_scatter/task_queue',
            '/internal/update_scatter/task_queue',
            '/internal/update_scatter/task_queue']
    params = [{'N': '1'}, {'N': '2'}, {'N': '3'}, {'N': '1'}, {'N': '2'}, {'N': '3'}]

    def __init__(self, *args, **kwargs):
        super(runUpdateAll, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        logging.info("plot update runned")
        for i in xrange(len(self.urls)):
            taskqueue.add(url=self.urls[i], params=self.params[i])



class UpdateHeatMapTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateHeatMapTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        import numpy, matplotlib, matplotlib.pyplot
        N = self.request.get("N")
        heatmap_plot = ndb.Key(Plot, "heatmap_plot_"+N).get()
        if heatmap_plot is not None:
            heatmap_plot.key.delete()
        words = ndb.gql('SELECT word, E, used_times FROM GlobalDictionaryWord').fetch()
        matplotlib.pyplot.title("heatmap")
        x = []
        y = []
        for word in words:
            if word.used_times >= int(N):
                x.append(len(word.word))
                y.append(int(word.E))

        heatmap, xedges, yedges = numpy.histogram2d(y, x, bins=[100, 100], range=[[0, 100], [0, 25]])
        extent = [0, 25, 0, 100]
        matplotlib.pyplot.clf()
        matplotlib.pyplot.axis([0, 25, 0, 100])
        matplotlib.pyplot.imshow(heatmap, extent=extent, aspect="auto", origin="lower")
        matplotlib.pyplot.title("heatmap for words, used >= {0} times".format(N))
        matplotlib.pyplot.xlabel("word length", fontsize=12)
        matplotlib.pyplot.ylabel("word difficulty", fontsize=12)
        rv = StringIO.StringIO()
        matplotlib.pyplot.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="heatmap_plot_"+N).put()
        matplotlib.pyplot.close()
        rv.close()


class UpdateScatterPlotTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateScatterPlotTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        import numpy, matplotlib, matplotlib.pyplot
        N = self.request.get("N")
        scatter_plot = ndb.Key(Plot, "scatter_plot_"+N).get()
        if scatter_plot is not None:
            scatter_plot.key.delete()
        words = ndb.gql('SELECT word, E, used_times FROM GlobalDictionaryWord').fetch()
        dict_words = {word.word:word.frequency for word
                      in ndb.gql('SELECT * FROM WordFrequency').fetch()}
        logging.info('{0} words in freq dictionary'.format(len(dict_words)))
        x = []
        y = []
        for word in words:
            if word.used_times >= int(N):
                if word.word in dict_words:
                    x.append(dict_words[word.word])
                    y.append(int(word.E))
        fig, ax = matplotlib.pyplot.subplots()
        ax.set_title("Scatter plot for words, used >= {0} times".format(N), fontsize=14)
        ax.set_xlabel("frequency", fontsize=12)
        ax.set_ylabel("difficulty", fontsize=12)
        ax.grid(True, linestyle='-',color='0.75')
        ax.plot(x, y, 'o', color="green", markersize=2)
        ax.set_xlim([0, 100])
        ax.set_ylim([0, 100])
        rv = StringIO.StringIO()
        fig.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="scatter_plot_"+N).put()
        matplotlib.pyplot.close()
        rv.close()





