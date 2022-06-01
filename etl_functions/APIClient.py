import hmac, hashlib;
import time;
import base64;
import requests;
import ntplib;

class APIClass:

	def __init__(self, public_key, private_key, request_uri, request_method, data = None, debug = False):

		c = ntplib.NTPClient();
		try:
			t = c.request('ntp.tascomi.com');
			the_time = time.strftime("%Y%m%d%H%M", time.localtime(t.offset + time.time())).encode('latin-1');
		except (ntplib.NTPException) as e:
			the_time = time.strftime("%Y%m%d%H%M").encode('latin-1'); 

		crypt = hashlib.sha256(public_key + the_time);
		token = crypt.hexdigest();
		hash = base64.b64encode(hmac.new(private_key, token.encode('latin-1'), hashlib.sha256).hexdigest().encode('latin-1')).decode('ascii');

		self.token = token;
		self.public_key = public_key.decode('latin-1');
		self.private_key = private_key.decode('latin-1');
		self.request_uri = request_uri;
		self.request_method = request_method;
		self.hash = hash;
		self.debug = debug;
		self.data = data;

	def sendRequest(self):

		headers = {'X-Public': self.public_key, 'X-Hash': self.hash, 'X-Debug': str(self.debug)}
		payload = self.data

		if self.request_method == 'GET':
			r = requests.get(self.request_uri, params=payload, headers=headers);
		elif self.request_method == 'POST':
			r = requests.post(self.request_uri, params=payload, headers=headers);
		elif self.request_method == 'PUT':
			r = requests.put(self.request_uri, params=payload, headers=headers);
		elif self.request_method == 'DELETE':
			r = requests.delete(self.request_uri, params=payload, headers=headers)

		self.status_code = r.status_code;

		if r.status_code == 200:

			self.json = r.json()

			#count = 0;
			#for iterator in self.json:

				#count = count + 1;

				#print("");
				#print("---- Result #" + str(count) + " ----");
				#print("");

				#for k, v in iterator.items():
					#print(str(k) + " --> " + str(v))

				#print("");
		else: 

			print(r)