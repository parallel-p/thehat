from handlers import ServiceRequestHandler

__author__ = 'ivan'

import StringIO
import logging

from google.appengine.ext import ndb
from google.appengine.api import taskqueue

from objects.global_dictionary import GlobalDictionaryWord


class Plot(ndb.Model):
    plot = ndb.BlobProperty(indexed=False)


class runUpdateAll(ServiceRequestHandler):
    urls = [
        '/internal/update_heatmap/task_queue',
        '/internal/update_heatmap/task_queue',
        '/internal/update_heatmap/task_queue',
        '/internal/update_scatter/task_queue',
        '/internal/update_scatter/task_queue',
        '/internal/update_scatter/task_queue',
        '/internal/update_d/task_queue']
    params = [{'N': '100'}, {'N': '50'}, {'N': '20'}, {'N': '100'}, {'N': '50'}, {'N': '20'}, {}]

    def __init__(self, *args, **kwargs):
        super(runUpdateAll, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        logging.info("plot update runned")
        from_admin = kwargs.get("admin") == "admin"
        for i in xrange(len(self.urls)):
            taskqueue.add(url=self.urls[i], params=self.params[i])
        if from_admin:
            self.redirect("/admin/logs_processing")


class UpdateDPlotHeatMapTaskQueue(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(UpdateDPlotHeatMapTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        import numpy, matplotlib, matplotlib.pyplot

        heatmap_plot = ndb.Key(Plot, "d_plot").get()
        if heatmap_plot is not None:
            heatmap_plot.key.delete()
        words = GlobalDictionaryWord.query(GlobalDictionaryWord.used_times > 0).fetch()
        matplotlib.pyplot.title("heatmap")
        x = []
        y = []
        max_used = 0
        for word in words:
            max_used = max(word.used_times, max_used)
            x.append(word.used_times)
            y.append(word.D)
        max_used = 8
        heatmap, xedges, yedges = numpy.histogram2d(y, x, bins=[30, max_used], range=[[0, 30], [0, max_used]])
        extent = [0, max_used, 0, 30]
        matplotlib.pyplot.clf()
        matplotlib.pyplot.axis(extent)
        matplotlib.pyplot.imshow(heatmap, extent=extent, aspect="auto", origin="lower")
        matplotlib.pyplot.title("heatmap for word used times to D")
        matplotlib.pyplot.xlabel("times used", fontsize=12)
        matplotlib.pyplot.ylabel("word D", fontsize=12)
        rv = StringIO.StringIO()
        matplotlib.pyplot.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="d_plot").put()
        matplotlib.pyplot.close()
        rv.close()


class UpdateHeatMapTaskQueue(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(UpdateHeatMapTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        import numpy, matplotlib, matplotlib.pyplot

        N = self.request.get("N")
        heatmap_plot = ndb.Key(Plot, "heatmap_plot_" + N).get()
        if heatmap_plot is not None:
            heatmap_plot.key.delete()
        q = GlobalDictionaryWord.query(GlobalDictionaryWord.used_times > 0).order(-GlobalDictionaryWord.used_times)
        count = int(q.count() * int(N) / 100)
        words = q.fetch(count)
        matplotlib.pyplot.title("heatmap")
        x = []
        y = []
        for word in words:
            x.append(len(word.word))
            y.append(int(word.E))

        heatmap, xedges, yedges = numpy.histogram2d(y, x, bins=[30, 25], range=[[0, 100], [0, 25]])
        extent = [0, 25, 0, 100]
        matplotlib.pyplot.clf()
        matplotlib.pyplot.axis([0, 25, 0, 100])
        matplotlib.pyplot.imshow(heatmap, vmin=1, extent=extent, aspect="auto", origin="lower")
        matplotlib.pyplot.title("heatmap for words in top {0} % used times".format(N))
        matplotlib.pyplot.xlabel("word length", fontsize=12)
        matplotlib.pyplot.ylabel("word difficulty", fontsize=12)
        rv = StringIO.StringIO()
        matplotlib.pyplot.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="heatmap_plot_" + N).put()
        matplotlib.pyplot.close()
        rv.close()


class UpdateScatterPlotTaskQueue(ServiceRequestHandler):
    def __init__(self, *args, **kwargs):
        super(UpdateScatterPlotTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        import matplotlib, matplotlib.pyplot

        N = self.request.get("N")
        scatter_plot = ndb.Key(Plot, "scatter_plot_" + N).get()
        if scatter_plot is not None:
            scatter_plot.key.delete()
        q = GlobalDictionaryWord.query(GlobalDictionaryWord.used_times > 0).order(-GlobalDictionaryWord.used_times)
        count = int(q.count() * int(N) / 100)
        words = q.fetch(count)
        dict_words = {word.word: word.frequency for word
                      in ndb.gql('SELECT * FROM WordFrequency').fetch()}
        logging.info('{0} words in freq dictionary'.format(len(dict_words)))
        x = []
        y = []
        for word in words:
            if word.word in dict_words:
                x.append(dict_words[word.word])
                y.append(int(word.E))
        fig, ax = matplotlib.pyplot.subplots()
        ax.set_title("Scatter plot for words in top {0} % used times".format(N), fontsize=14)
        ax.set_xlabel("uses per million words", fontsize=12)
        ax.set_ylabel("difficulty", fontsize=12)
        ax.grid(True, linestyle='-', color='0.75')
        ax.plot(x, y, 'o', color="green", markersize=2)
        ax.set_xscale('log')
        ax.set_ylim([0, 100])
        rv = StringIO.StringIO()
        fig.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="scatter_plot_" + N).put()
        matplotlib.pyplot.close()
        rv.close()





