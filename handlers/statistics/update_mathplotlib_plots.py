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


class DictionaryWord(ndb.Model):

    word = ndb.StringProperty()
    difficulty = ndb.IntegerProperty()


class MakeDictionaryTaskQueueHandler(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeDictionaryTaskQueueHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        words = json.loads(self.request.get("json"))
        for word in words:
            DictionaryWord(word=word["word"], difficulty=int(word["difficulty"]), id=word["word"]).put()


class MakeDictionaryHandler(AdminRequestHandler):

    def __init__(self, *args, **kwargs):
        super(MakeDictionaryHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        in_json = json.loads(self.request.get("json"))
        to_add = []
        for word in in_json:
            in_base = ndb.Key(DictionaryWord, word["word"]).get()
            if in_base is not None:
                to_add.append(word)
        taskqueue.add(url='/internal/add_dictionary/task_queue', params={"json": json.dumps(to_add)})

    def get(self, *args, **kwargs):
        self.draw_page("statistics/add_words_to_dict")


class UpdateHeatMapTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateHeatMapTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        heatmap_plot = ndb.Key(Plot, "heatmap_plot").get()
        if heatmap_plot is not None:
            heatmap_plot.key.delete()
        words = ndb.gql('SELECT word, E, used_times FROM GlobalDictionaryWord').fetch()
        matplotlib.pyplot.title("heatmap")
        x = []
        y = []
        for word in words:
            if word.used_times > 0:
                x.append(len(word.word))
                y.append(int(word.E))
        logging.info('x' + " ".join([str(i) for i in x]))
        logging.info('y' + " ".join([str(i) for i in y]))

        heatmap, xedges, yedges = numpy.histogram2d(x, y, bins=50)
        extent = [xedges[0], xedges[-1], yedges[0], yedges[-1]]
        matplotlib.pyplot.clf()
        matplotlib.pyplot.axis([min(x), max(x), min(y), max(y)])
        matplotlib.pyplot.imshow(heatmap, extent=extent, aspect="auto", origin="lower")
        matplotlib.pyplot.title("heatmap")
        matplotlib.pyplot.xlabel("word length", fontsize=12)
        matplotlib.pyplot.ylabel("word difficulty", fontsize=12)
        rv = StringIO.StringIO()
        matplotlib.pyplot.savefig(rv, format="png")
        Plot(plot=rv.getvalue(), id="heatmap_plot").put()
        matplotlib.pyplot.close()
        rv.close()


class UpdateScatterPlotTaskQueue(ServiceRequestHandler):

    def __init__(self, *args, **kwargs):
        super(UpdateScatterPlotTaskQueue, self).__init__(*args, **kwargs)

    def post(self):
        scatter_plot = ndb.Key(Plot, "scatter_plot").get()
        if scatter_plot is not None:
            scatter_plot.key.delete()
        words = ndb.gql('SELECT word, E, used_times FROM GlobalDictionaryWord').fetch()
        dict_words = {word.word:word.difficulty for word
                      in ndb.gql('SELECT * FROM DictionaryWord').fetch()}
        x = []
        y = []
        for word in words:
            if word.used_times > 0:
                if word.word in dict_words:
                    x.append(dict_words[word.word])
                    y.append(int(word.E))

        fig, ax = matplotlib.pyplot.subplots()
        ax.set_title("Scatter plot",fontsize=14)
        ax.set_xlabel("frequency", fontsize=12)
        ax.set_ylabel("difficulty", fontsize=12)
        ax.grid(True, linestyle='-',color='0.75')
        ax.plot(x, y, 'o', color="green", markersize=10)
        ax.set_xlim([0, 10])
        ax.set_ylim([0, 100])
        rv = StringIO.StringIO()
        fig.savefig(rv, format="png", dpi=100)
        Plot(plot=rv.getvalue(), id="scatter_plot").put()
        matplotlib.pyplot.close()
        rv.close()





