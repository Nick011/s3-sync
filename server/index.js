var cluster = require('cluster')
  , http = require('http')
  , sio = require('socket.io')
  , redis = require('redis')
  , port = process.env.PORT || 8000
  , numCPUs = require('os').cpus().length
  , RedisStore = sio.RedisStore;

//else it's a worker process, boot up a server
var httpServer = http.createServer().listen(port)
  , io = sio.listen(httpServer);

//configure redis to go
var rtg = {
  port: 6379, 
  hostname: process.env.REDIS_HOST || 'localhost',
  password: process.env.REDIS_PASSWORD || ''
};

var pub = redis.createClient(rtg.port, rtg.hostname);
pub.auth(rtg.password);
var sub = redis.createClient(rtg.port, rtg.hostname);
sub.auth(rtg.password);
var client = redis.createClient(rtg.port, rtg.hostname);
client.auth(rtg.password);


// configure socket.io
io.configure(function() {
  //create redis connection, set options
  var redisStore = new RedisStore({redis: redis,
                                   redisPub: pub,
                                   redisSub: sub,
                                   redisClient: client});

  io.set('store', redisStore);
  io.set('log level', 0);

});


//socket.io routing
io.sockets.on('connection', function(socket) {
  //on connection, call connect and pass a dict
  //ex {username: (username), user_id: (uid) organization_id: (orgid)}
  io.sockets.emit('create', {test:'test'});

  //handle user disconnect
  socket.on('create', function(req) {
    console.log(req);
    io.sockets.emit('create', req);
  });

  //handle post routes
  socket.on('delete', function(req) {
    console.log(req);
    //chat.group(io, socket, req);
    io.sockets.emit('delete', req);
  });


});
