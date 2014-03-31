__author__ = 'ivan'


from google.appengine.ext import ndb
from handlers.base_handlers.admin_request_handler import AdminRequestHandler
from handlers.base_handlers.service_request_handler import ServiceRequestHandler
import StringIO
import numpy, matplotlib, matplotlib.pyplot
from google.appengine.api import taskqueue
import json
import logging


class Plot(ndb.Model):

    plot = ndb.BlobProperty(indexed=False)


class WordFrequency(ndb.Model):

    word = ndb.StringProperty()
    frequency = ndb.IntegerProperty()


class MakeDictionaryTaskQueueHandler(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeDictionaryTaskQueueHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        words = json.loads(self.request.get("json"))
        for word in words:
            WordFrequency(word=word["w"], frequency=int(word["d"]), id=word["w"]).put()


class MakeDictionaryHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        in_json = json.loads(self.request.get("json"))
        to_add = []
        for word in in_json:
            to_add.append(word)
        taskqueue.add(url='/internal/add_dictionary/task_queue', params={"json": json.dumps(to_add)})


class UpdateHeatMapTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateHeatMapTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
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

        heatmap, xedges, yedges = numpy.histogram2d(x, y, bins=50)
        extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
        matplotlib.pyplot.clf()
        matplotlib.pyplot.axis([min(x), max(x), min(y), max(y)])
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
        ax.set_title("Scatter plot for words, used >= {0} times", fontsize=14)
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





