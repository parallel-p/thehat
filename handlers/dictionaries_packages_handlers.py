import json
from objects.user_devices import get_user_by_device
from objects.user_streams import UserStreams
from objects.dictionaries_packages import PackagesStream, PackageDictionary
from base_handlers.api_request_handlers import APIRequestHandler, AuthorizedAPIRequestHandler


class GetStreamsListHandler(APIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GetStreamsListHandler, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        streams_list = PackagesStream.query()
        json_obj = {'streams': []}
        for stream in streams_list:
            json_obj['streams'].append({'id': stream.id, 'name': stream.name})

        self.response.write(json.dumps(json_obj))


class ChangeStreamStateHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(ChangeStreamStateHandler, self).__init__(*args, **kwargs)

    def post(self, *args, **kwargs):
        super(ChangeStreamStateHandler, self).authorizate(**kwargs)
        subscribe_list = UserStreams.query(ancestor=self.user_key).fetch(1)
        if len(subscribe_list) == 0:
            self.error(404)
        else:
            stream_id = kwargs.get('stream_id')
            if kwargs.get('on', '') == 'true':
                if stream_id not in subscribe_list[0].streams:
                    subscribe_list[0].streams.append(stream_id)
            else:
                if stream_id in subscribe_list[0].streams:
                    subscribe_list[0].streams.remove(stream_id)


class GetPackagesListHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GetPackagesListHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(GetPackagesListHandler, self).authorizate(**kwargs)
        packages_stream = PackagesStream.query(PackagesStream.id == kwargs.get('stream_id')).fetch(1)

        if len(packages_stream) == 0:
            self.error(404)
        else:
            packages_list = []
            for package_id in packages_stream[0].packages_id_list:
                packages = PackageDictionary.query(PackageDictionary.id == package_id).fetch(1)
                if len(packages) == 0:
                    self.error(404)
                packages_list.append(packages[0])
            json_obj = {'packages': []}
            for package in packages_list:
                json_obj['packages'].append(
                    {'id': package.id, 'name': package.name, 'release_time': package.release_time})

            self.response.write(json.dumps(json_obj))


class GetPackageHandler(AuthorizedAPIRequestHandler):
    def __init__(self, *args, **kwargs):
        super(GetPackageHandler, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        super(GetPackageHandler, self).authorizate(**kwargs)
        packages = PackageDictionary.query(PackageDictionary.id == kwargs.get('package_id')).fetch(1)

        if len(packages) == 0:
            self.error(404)
        else:
            package = packages[0]
            json_obj = {"id": package.id, "name": package.name, "release_time": package.release_time,
                        "words": package.words}

            self.response.write(json.dumps(json_obj))
