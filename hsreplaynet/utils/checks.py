from django.core import checks


REDIS_MINIMUM_VERSION = (3, 0, 0)


@checks.register()
def check_redis(app_configs=None, **kwargs):
	from django_rq.queues import get_queue

	errors = []

	try:
		queue = get_queue()
	except Exception as e:
		conn_settings = queue.connection.connection_pool.connection_kwargs
		errors.append(checks.Error(
			"Could not connect to redis: %s") % (e),
			hint="Attempted to connect with the following settings: %s" % (conn_settings)
		)

	version = queue.connection.info()["redis_version"]
	version_tuple = tuple(int(x) for x in version.split("."))

	if version_tuple < REDIS_MINIMUM_VERSION:
		errors.append(checks.Error(
			"Your version of redis is too old (found %s)" % (version),
			hint="Minimum version required: %s" % (REDIS_MINIMUM_VERSION)
		))

	return errors
