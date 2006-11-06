#!/usr/bin/env python2.4
"""
httplib2test

A set of unit tests for httplib2.py.

Requires Python 2.4 or later
"""

__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__license__ = "MIT"
__history__ = """ """
__version__ = "0.1 ($Rev: 118 $)"


import unittest, httplib2, os, urlparse, time, base64


# Python 2.3 support
if not hasattr(unittest.TestCase, 'assertTrue'):
    unittest.TestCase.assertTrue = unittest.TestCase.failUnless
    unittest.TestCase.assertFalse = unittest.TestCase.failIf

# The test resources base uri
base = 'http://bitworking.org/projects/httplib2/test/'
#base = 'http://localhost/projects/httplib2/test/'

class ParserTest(unittest.TestCase):
    def testFromStd66(self):
        self.assertEqual( ('http', 'example.com', '', None, None ), httplib2.parse_uri("http://example.com"))
        self.assertEqual( ('https', 'example.com', '', None, None ), httplib2.parse_uri("https://example.com"))
        self.assertEqual( ('https', 'example.com:8080', '', None, None ), httplib2.parse_uri("https://example.com:8080"))
        self.assertEqual( ('http', 'example.com', '/', None, None ), httplib2.parse_uri("http://example.com/"))
        self.assertEqual( ('http', 'example.com', '/path', None, None ), httplib2.parse_uri("http://example.com/path"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', None ), httplib2.parse_uri("http://example.com/path?a=1&b=2"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', 'fred' ), httplib2.parse_uri("http://example.com/path?a=1&b=2#fred"))
        self.assertEqual( ('http', 'example.com', '/path', 'a=1&b=2', 'fred' ), httplib2.parse_uri("http://example.com/path?a=1&b=2#fred"))


class HttpTest(unittest.TestCase):
    def setUp(self):
        cacheDirName = ".cache"
        if os.path.exists(cacheDirName): 
            [os.remove(os.path.join(cacheDirName, file)) for file in os.listdir(cacheDirName)]
        self.http = httplib2.Http(cacheDirName)
        self.http.clear_credentials()

    def testGetIsDefaultMethod(self):
        # Test that GET is the default method
        uri = urlparse.urljoin(base, "methods/method_reflector.cgi")
        (response, content) = self.http.request(uri)
        self.assertEqual(response['x-method'], "GET")

    def testDifferentMethods(self):
        # Test that all methods can be used
        uri = urlparse.urljoin(base, "methods/method_reflector.cgi")
        for method in ["GET", "PUT", "DELETE", "POST"]:
            (response, content) = self.http.request(uri, method, body=" ")
            self.assertEqual(response['x-method'], method)

    def testGetNoCache(self):
        # Test that can do a GET w/o the cache turned on.
        http = httplib2.Http()
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.previous, None)

    def testGetOnlyIfCachedCacheMiss(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        http = httplib2.Http()
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 200)

    def testGetOnlyIfCachedNoCacheAtAll(self):
        # Test that can do a GET with no cache with 'only-if-cached'
        # Of course, there might be an intermediary beyond us
        # that responds to the 'only-if-cached', so this
        # test can't really be guaranteed to pass.
        http = httplib2.Http()
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = http.request(uri, "GET", headers={'cache-control': 'only-if-cached'})
        self.assertEqual(response.fromcache, False)
        self.assertEqual(response.status, 200)

    def testUserAgent(self):
        # Test that we provide a default user-agent
        uri = urlparse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith("Python-httplib2/"))

    def testUserAgentNonDefault(self):
        # Test that the default user-agent can be over-ridden
        uri = urlparse.urljoin(base, "user-agent/test.cgi")
        (response, content) = self.http.request(uri, "GET", headers={'User-Agent': 'fred/1.0'})
        self.assertEqual(response.status, 200)
        self.assertTrue(content.startswith("fred/1.0"))

    def testGet300WithLocation(self):
        # Test the we automatically follow 300 redirects if a Location: header is provided
        uri = urlparse.urljoin(base, "300/with-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

        # Confirm that the intermediate 300 is not cached
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 300)
        self.assertEqual(response.previous.fromcache, False)

    def testGet300WithoutLocation(self):
        # Not giving a Location: header in a 300 response is acceptable
        # In which case we just return the 300 response
        uri = urlparse.urljoin(base, "300/without-location-header.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 300)
        self.assertTrue(response['content-type'].startswith("text/html"))
        self.assertEqual(response.previous, None)

    def testGet301(self):
        # Test that we automatically follow 301 redirects
        # and that we cache the 301 response
        uri = urlparse.urljoin(base, "301/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 301)
        self.assertEqual(response.previous.fromcache, True)

    def testGet302(self):
        # Test that we automatically follow 302 redirects
        # and that we DO NOT cache the 302 response
        uri = urlparse.urljoin(base, "302/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

        uri = urlparse.urljoin(base, "302/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

        uri = urlparse.urljoin(base, "302/twostep.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 302)
        self.assertEqual(response.previous.fromcache, False)

    def testGet302RedirectionLimit(self):
        # Test that we can set a lower redirection limit
        # and that we raise an exception when we exceed
        # that limit.
        uri = urlparse.urljoin(base, "302/twostep.asis")
        try:
            (response, content) = self.http.request(uri, "GET", redirections = 1)
            self.fail("This should not happen")
        except httplib2.RedirectLimit:
            pass
        except Exception, e:
            self.fail("Threw wrong kind of exception ")

    def testGet302NoLocation(self):
        # Test that we throw an exception when we get
        # a 302 with no Location: header.
        uri = urlparse.urljoin(base, "302/no-location.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.RedirectMissingLocation:
            pass
        except Exception, e:
            self.fail("Threw wrong kind of exception ")

    def testGet302ViaHttps(self):
        # Google always redirects to http://google.com
        (response, content) = self.http.request("https://google.com", "GET")
        self.assertEqual(200, response.status)
        self.assertEqual(302, response.previous.status)

    def testGetViaHttps(self):
        # Test that we can handle HTTPS
        (response, content) = self.http.request("https://google.com/adsense/", "GET")
        self.assertEqual(200, response.status)
        self.assertEqual(None, response.previous)

    def testGetViaHttpsSpecViolationOnLocation(self):
        # Test that we follow redirects through HTTPS
        # even if they violate the spec by including
        # a relative Location: header instead of an 
        # absolute one.
        (response, content) = self.http.request("https://google.com/adsense", "GET")
        self.assertEqual(200, response.status)
        self.assertNotEqual(None, response.previous)

    def testGet303(self):
        # Do a follow-up GET on a Location: header
        # returned from a POST that gave a 303.
        uri = urlparse.urljoin(base, "303/303.cgi")
        (response, content) = self.http.request(uri, "POST", " ")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 303)

    def test303ForDifferentMethods(self):
        # Test that all methods can be used
        uri = urlparse.urljoin(base, "303/redirect-to-reflector.cgi")
        # HEAD really does send a HEAD, but apparently Apache changes 
        # every HEAD into a GET, so our script returns x-method: GET.
        for (method, method_on_303) in [("PUT", "GET"), ("DELETE", "GET"), ("POST", "GET"), ("GET", "GET"), ("HEAD", "GET")]: 
            (response, content) = self.http.request(uri, method, body=" ")
            self.assertEqual(response['x-method'], method_on_303)

    def testGet304(self):
        # Test that we use ETags properly to validate our cache
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'must-revalidate'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "HEAD")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers = {'range': 'bytes=0-0'})
        self.assertEqual(response.status, 206)
        self.assertEqual(response.fromcache, False)

    def testGetIgnoreEtag(self):
        # Test that we can forcibly ignore ETags 
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")

        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_IF_NONE_MATCH')) 

        self.http.ignore_etag = True
        (response, content) = self.http.request(uri, "GET", headers = {'cache-control': 'max-age=0'})
        d = self.reflector(content)
        self.assertEqual(response.fromcache, False)
        self.assertFalse(d.has_key('HTTP_IF_NONE_MATCH')) 


    def testGet304EndToEnd(self):
       # Test that end to end headers get overwritten in the cache
        uri = urlparse.urljoin(base, "304/end2end.cgi")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")
        old_date = response['date']
        time.sleep(2)

        (response, content) = self.http.request(uri, "GET", headers = {'Cache-Control': 'max-age=0'})
        # The response should be from the cache, but the Date: header should be updated.
        new_date = response['date']
        self.assertNotEqual(new_date, old_date)
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

    def testGet304LastModified(self):
        # Test that we can still handle a 304 
        # by only using the last-modified cache validator.
        uri = urlparse.urljoin(base, "304/last-modified-only/last-modified-only.txt")
        (response, content) = self.http.request(uri, "GET")

        self.assertNotEqual(response['last-modified'], "")
        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

    def testGet307(self):
        # Test that we do follow 307 redirects but
        # do not cache the 307
        uri = urlparse.urljoin(base, "307/onestep.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        self.assertEqual(content, "This is the final destination.\n")
        self.assertEqual(response.previous.status, 307)
        self.assertEqual(response.previous.fromcache, False)

    def testGet410(self):
        # Test that we pass 410's through
        uri = urlparse.urljoin(base, "410/410.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 410)

    def testGetGZip(self):
        # Test that we support gzip compression
        uri = urlparse.urljoin(base, "gzip/final-destination.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-encoding'], "gzip")
        self.assertEqual(int(response['content-length']), len("This is the final destination.\n"))
        self.assertEqual(content, "This is the final destination.\n")

    def testGetGZipFailure(self):
        # Test that we raise a good exception when the gzip fails
        uri = urlparse.urljoin(base, "gzip/failed-compression.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.FailedToDecompressContent:
            pass
        except Exception:
            self.fail("Threw wrong kind of exception")

    def testGetDeflate(self):
        # Test that we support deflate compression
        uri = urlparse.urljoin(base, "deflate/deflated.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response['content-encoding'], "deflate")
        self.assertEqual(int(response['content-length']), len("This is the final destination."))
        self.assertEqual(content, "This is the final destination.")

    def testGetDeflateFailure(self):
        # Test that we raise a good exception when the deflate fails
        uri = urlparse.urljoin(base, "deflate/deflated.asis")
        uri = urlparse.urljoin(base, "deflate/failed-compression.asis")
        try:
            (response, content) = self.http.request(uri, "GET")
            self.fail("Should never reach here")
        except httplib2.FailedToDecompressContent:
            pass
        except Exception:
            self.fail("Threw wrong kind of exception")

    def testGetDuplicateHeaders(self):
        # Test that duplicate headers get concatenated via ','
        uri = urlparse.urljoin(base, "duplicate-headers/multilink.asis")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(content, "This is content\n")
        self.assertEqual(response['link'].split(",")[0], '<http://bitworking.org>; rel="home"; title="BitWorking"')

    def testGetCacheControlNoCache(self):
        # Test Cache-Control: no-cache on requests
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlPragmaNoCache(self):
        # Test Pragma: no-cache on requests
        uri = urlparse.urljoin(base, "304/test_etag.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertNotEqual(response['etag'], "")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)

        (response, content) = self.http.request(uri, "GET", headers={'Pragma': 'no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreRequest(self):
        # A no-store request means that the response should not be stored.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoStoreResponse(self):
        # A no-store response means that the response should not be stored.
        uri = urlparse.urljoin(base, "no-store/no-store.asis")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testGetCacheControlNoCacheNoStoreRequest(self):
        # Test that a no-store, no-cache clears the entry from the cache
        # even if it was cached previously.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store, no-cache'})
        (response, content) = self.http.request(uri, "GET", headers={'Cache-Control': 'no-store, no-cache'})
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)

    def testUpdateInvalidatesCache(self):
        # Test that calling PUT or DELETE on a 
        # URI that is cache invalidates that cache.
        uri = urlparse.urljoin(base, "304/test_etag.txt")

        (response, content) = self.http.request(uri, "GET")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "DELETE")
        self.assertEqual(response.status, 405)

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.fromcache, False)

    def testUpdateUsesCachedETag(self):
        # Test that we natively support http://www.w3.org/1999/04/Editing/ 
        uri = urlparse.urljoin(base, "conditional-updates/test.cgi")

        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, False)
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.fromcache, True)
        (response, content) = self.http.request(uri, "PUT")
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "PUT")
        self.assertEqual(response.status, 412)

    def testBasicAuth(self):
        # Test Basic Authentication
        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthTwoDifferentCredentials(self):
        # Test Basic Authentication with multiple sets of credentials
        uri = urlparse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic2/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic2/file.txt")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testBasicAuthNested(self):
        # Test Basic Authentication with resources
        # that are nested
        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        # Now add in credentials one at a time and test.
        self.http.add_credentials('joe', 'password')

        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('fred', 'barney')

        uri = urlparse.urljoin(base, "basic-nested/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "basic-nested/subdir")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

    def testDigestAuth(self):
        # Test that we support Digest Authentication
        uri = urlparse.urljoin(base, "digest/")
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 401)

        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET")
        self.assertEqual(response.status, 200)

        uri = urlparse.urljoin(base, "digest/file.txt")
        (response, content) = self.http.request(uri, "GET")

    def testDigestAuthNextNonceAndNC(self):
        # Test that if the server sets nextnonce that we reset
        # the nonce count back to 1
        uri = urlparse.urljoin(base, "digest/file.txt")
        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info2 = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

        if info.has_key('nextnonce'):
            self.assertEqual(info2['nc'], 1)

    def testDigestAuthStale(self):
        # Test that we can handle a nonce becoming stale
        uri = urlparse.urljoin(base, "digest-expire/file.txt")
        self.http.add_credentials('joe', 'password')
        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        info = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

        time.sleep(3)
        # Sleep long enough that the nonce becomes stale

        (response, content) = self.http.request(uri, "GET", headers = {"cache-control":"no-cache"})
        self.assertFalse(response.fromcache)
        self.assertTrue(response._stale_digest)
        info3 = httplib2._parse_www_authenticate(response, 'authentication-info')
        self.assertEqual(response.status, 200)

    def reflector(self, content):
        return  dict( [tuple(x.split("=", 1)) for x in content.strip().split("\n")] )

    def testReflector(self):
        uri = urlparse.urljoin(base, "reflector/reflector.cgi")
        (response, content) = self.http.request(uri, "GET")
        d = self.reflector(content)
        self.assertTrue(d.has_key('HTTP_USER_AGENT')) 

try:
    import memcache
    class HttpTestMemCached(HttpTest):
        def setUp(self):
            self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)
            #self.cache = memcache.Client(['10.0.0.4:11211'], debug=1)
            self.http = httplib2.Http(self.cache)
            self.cache.flush_all()
            # Not exactly sure why the sleep is needed here, but
            # if not present then some unit tests that rely on caching
            # fail. Memcached seems to lose some sets immediately
            # after a flush_all if the set is to a value that
            # was previously cached. (Maybe the flush is handled async?)
            time.sleep(1)
            self.http.clear_credentials()
except:
    pass



# ------------------------------------------------------------------------

class HttpPrivateTest(unittest.TestCase):

    def testParseCacheControl(self):
        # Test that we can parse the Cache-Control header
        self.assertEqual({}, httplib2._parse_cache_control({}))
        self.assertEqual({'no-cache': 1}, httplib2._parse_cache_control({'cache-control': ' no-cache'}))
        cc = httplib2._parse_cache_control({'cache-control': ' no-cache, max-age = 7200'})
        self.assertEqual(cc['no-cache'], 1)
        self.assertEqual(cc['max-age'], '7200')
        cc = httplib2._parse_cache_control({'cache-control': ' , '})
        self.assertEqual(cc[''], 1)

    def testNormalizeHeaders(self):
        # Test that we normalize headers to lowercase 
        h = httplib2._normalize_headers({'Cache-Control': 'no-cache', 'Other': 'Stuff'})
        self.assertTrue(h.has_key('cache-control'))
        self.assertTrue(h.has_key('other'))
        self.assertEqual('Stuff', h['other'])

    def testExpirationModelTransparent(self):
        # Test that no-cache makes our request TRANSPARENT
        response_headers = {
            'cache-control': 'max-age=7200'
        }
        request_headers = {
            'cache-control': 'no-cache'
        }
        self.assertEqual("TRANSPARENT", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelNoCacheResponse(self):
        # The date and expires point to an entry that should be
        # FRESH, but the no-cache over-rides that.
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+4)),
            'cache-control': 'no-cache'
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelStaleRequestMustReval(self):
        # must-revalidate forces STALE
        self.assertEqual("STALE", httplib2._entry_disposition({}, {'cache-control': 'must-revalidate'}))

    def testExpirationModelStaleResponseMustReval(self):
        # must-revalidate forces STALE
        self.assertEqual("STALE", httplib2._entry_disposition({'cache-control': 'must-revalidate'}, {}))

    def testExpirationModelFresh(self):
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            'cache-control': 'max-age=2'
        }
        request_headers = {
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))
        time.sleep(3)
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationMaxAge0(self):
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
            'cache-control': 'max-age=0'
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpires(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+2)),
        }
        request_headers = {
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))
        time.sleep(3)
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateOnly(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+3)),
        }
        request_headers = {
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelOnlyIfCached(self):
        response_headers = {
        }
        request_headers = {
            'cache-control': 'only-if-cached',
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelMaxAgeBoth(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'cache-control': 'max-age=2'
        }
        request_headers = {
            'cache-control': 'max-age=0'
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpiresMinFresh1(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+2)),
        }
        request_headers = {
            'cache-control': 'min-fresh=2'
        }
        self.assertEqual("STALE", httplib2._entry_disposition(response_headers, request_headers))

    def testExpirationModelDateAndExpiresMinFresh2(self):
        now = time.time()
        response_headers = {
            'date': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now)),
            'expires': time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now+4)),
        }
        request_headers = {
            'cache-control': 'min-fresh=2'
        }
        self.assertEqual("FRESH", httplib2._entry_disposition(response_headers, request_headers))

    def testParseWWWAuthenticateEmpty(self):
        res = httplib2._parse_www_authenticate({})
        self.assertEqual(len(res.keys()), 0) 

    def testParseWWWAuthenticate(self):
        # different uses of spaces around commas
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="test realm" , foo=foo ,bar="bar", baz=baz,qux=qux'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(len(res['test'].keys()), 5)
        
        # tokens with non-alphanum
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'T*!%#st realm=to*!%#en, to*!%#en="quoted string"'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(len(res['t*!%#st'].keys()), 2)
        
        # quoted string with quoted pairs
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Test realm="a \\"test\\" realm"'})
        self.assertEqual(len(res.keys()), 1)
        self.assertEqual(res['test']['realm'], 'a "test" realm')

    def testParseWWWAuthenticateStrict(self):
        httplib2.USE_WWW_AUTH_STRICT_PARSING = 1;
        self.testParseWWWAuthenticate();
        httplib2.USE_WWW_AUTH_STRICT_PARSING = 0;

    def testParseWWWAuthenticateBasic(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me"'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me", algorithm="MD5"'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('MD5', basic['algorithm'])

        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me", algorithm=MD5'})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('MD5', basic['algorithm'])

    def testParseWWWAuthenticateBasic2(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic realm="me",other="fred" '})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        self.assertEqual('fred', basic['other'])

    def testParseWWWAuthenticateBasic3(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 'Basic REAlm="me" '})
        basic = res['basic']
        self.assertEqual('me', basic['realm'])


    def testParseWWWAuthenticateDigest(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41"'})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])


    def testParseWWWAuthenticateMultiple(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41" Basic REAlm="me" '})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

    def testParseWWWAuthenticateMultiple2(self):
        # Handle an added comma between challenges, which might get thrown in if the challenges were
        # originally sent in separate www-authenticate headers.
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me" '})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])

    def testParseWWWAuthenticateMultiple3(self):
        # Handle an added comma between challenges, which might get thrown in if the challenges were
        # originally sent in separate www-authenticate headers.
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="testrealm@host.com", qop="auth,auth-int", nonce="dcd98b7102dd2f0e8b11d0f600bfb0c093", opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me", WSSE realm="foo", profile="UsernameToken"'})
        digest = res['digest']
        self.assertEqual('testrealm@host.com', digest['realm'])
        self.assertEqual('auth,auth-int', digest['qop'])
        self.assertEqual('dcd98b7102dd2f0e8b11d0f600bfb0c093', digest['nonce'])
        self.assertEqual('5ccc069c403ebaf9f0171e9517f40e41', digest['opaque'])
        basic = res['basic']
        self.assertEqual('me', basic['realm'])
        wsse = res['wsse']
        self.assertEqual('foo', wsse['realm'])
        self.assertEqual('UsernameToken', wsse['profile'])

    def testParseWWWAuthenticateMultiple4(self):
        res = httplib2._parse_www_authenticate({ 'www-authenticate': 
                'Digest realm="test-real.m@host.com", qop \t=\t"\tauth,auth-int", nonce="(*)&^&$%#",opaque="5ccc069c403ebaf9f0171e9517f40e41", Basic REAlm="me", WSSE realm="foo", profile="UsernameToken"'}) 
        digest = res['digest']
        self.assertEqual('test-real.m@host.com', digest['realm'])
        self.assertEqual('\tauth,auth-int', digest['qop'])
        self.assertEqual('(*)&^&$%#', digest['nonce'])

    def testParseWWWAuthenticateMoreQuoteCombos(self):
        res = httplib2._parse_www_authenticate({'www-authenticate':'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'})
        digest = res['digest']
        self.assertEqual('myrealm', digest['realm'])

    def testDigestObject(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = {
            'www-authenticate': 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth"'
        }
        content = ""
        
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        d.request("GET", request_uri, headers, content, cnonce="33033375ec278a46") 
        our_request = "Authorization: %s" % headers['Authorization']
        working_request = 'Authorization: Digest username="joe", realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", uri="/projects/httplib2/test/digest/", algorithm=MD5, response="97ed129401f7cdc60e5db58a80f3ea8b", qop=auth, nc=00000001, cnonce="33033375ec278a46"'
        self.assertEqual(our_request, working_request)


    def testDigestObjectStale(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = httplib2.Response({ })
        response['www-authenticate'] = 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'
        response.status = 401
        content = ""
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        # Returns true to force a retry
        self.assertTrue( d.response(response, content) )

    def testDigestObjectAuthInfo(self):
        credentials = ('joe', 'password')
        host = None
        request_uri = '/projects/httplib2/test/digest/' 
        headers = {}
        response = httplib2.Response({ })
        response['www-authenticate'] = 'Digest realm="myrealm", nonce="Ygk86AsKBAA=3516200d37f9a3230352fde99977bd6d472d4306", algorithm=MD5, qop="auth", stale=true'
        response['authentication-info'] = 'nextnonce="fred"'
        content = ""
        d = httplib2.DigestAuthentication(credentials, host, request_uri, headers, response, content, None)
        # Returns true to force a retry
        self.assertFalse( d.response(response, content) )
        self.assertEqual('fred', d.challenge['nonce'])
        self.assertEqual(1, d.challenge['nc'])

    def testWsseAlgorithm(self):
        digest = httplib2._wsse_username_token("d36e316282959a9ed4c89851497a717f", "2003-12-15T14:43:07Z", "taadtaadpstcsm")
        expected = "quR/EWLAV4xLf9Zqyw4pDmfV9OY="
        self.assertEqual(expected, digest)

    def testEnd2End(self):
        # one end to end header
        response = {'content-type': 'application/atom+xml', 'te': 'deflate'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertTrue('content-type' in end2end)
        self.assertTrue('te' not in end2end)
        self.assertTrue('connection' not in end2end)

        # one end to end header that gets eliminated
        response = {'connection': 'content-type', 'content-type': 'application/atom+xml', 'te': 'deflate'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertTrue('content-type' not in end2end)
        self.assertTrue('te' not in end2end)
        self.assertTrue('connection' not in end2end)

        # Degenerate case of no headers
        response = {}
        end2end = httplib2._get_end2end_headers(response)
        self.assertEquals(0, len(end2end))

        # Degenerate case of connection referrring to a header not passed in 
        response = {'connection': 'content-type'}
        end2end = httplib2._get_end2end_headers(response)
        self.assertEquals(0, len(end2end))

unittest.main()

