## 0.6.0

* kmsauth will use lru-dict library for its token cache, rather than a slower pure-python implementation, if lru-dict is available.

## 0.5.0

* KMSTokenValidator now accepts a ``stats`` argument, which allows you to pass in an instance of a statsd client, so that the validator can track stats.

## 0.4.0

* KMSTokenValidator now accepts a ``token_cache_size`` argument, to set the size of the in-memory LRU token cache.

## 0.3.0

* python3 compat
