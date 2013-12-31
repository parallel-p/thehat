__author__ = 'ivan'

from all_handler import AllHandler

class ComplainWordHandler(AllHandler):
    def post(self, **kwargs):
        super(ComplainWordHandler, self).set_device_id(**kwargs)
        self.response.write('post, ok, device_id = {0}'.format(self.device_id))
