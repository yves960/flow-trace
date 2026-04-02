# Java调用模式参考

本文档列出flow-trace技能可识别的Java调用模式。

## HTTP调用

### RestTemplate
```java
// GET请求
restTemplate.getForObject(url, Response.class);
restTemplate.getForEntity(url, Response.class);

// POST请求
restTemplate.postForObject(url, request, Response.class);
restTemplate.postForEntity(url, request, Response.class);

// PUT/DELETE
restTemplate.put(url, request);
restTemplate.delete(url);
```

### WebClient (Spring WebFlux)
```java
webClient.get()
    .uri("/api/users/{id}", userId)
    .retrieve()
    .bodyToMono(User.class);

webClient.post()
    .uri("/api/orders")
    .bodyValue(orderRequest)
    .retrieve()
    .bodyToMono(Order.class);
```

### Feign Client
```java
@FeignClient(name = "user-service", url = "${user-service.url}")
public interface UserClient {
    @GetMapping("/api/users/{id}")
    User getUser(@PathVariable("id") Long id);
    
    @PostMapping("/api/users")
    User createUser(@RequestBody UserRequest request);
}
```

### OkHttp
```java
OkHttpClient client = new OkHttpClient();
Request request = new Request.Builder()
    .url("http://user-service/api/users/1")
    .build();
Response response = client.newCall(request).execute();
```

## RPC调用

### Dubbo
```java
@Reference(version = "1.0.0")
private UserService userService;

public User getUser(Long id) {
    return userService.getById(id);
}
```

### gRPC
```java
@GrpcClient("user-service")
private UserServiceGrpc.UserServiceBlockingStub userServiceStub;

public UserResponse getUser(Long id) {
    UserRequest request = UserRequest.newBuilder().setId(id).build();
    return userServiceStub.getUser(request);
}
```

## 消息队列

### Kafka Producer
```java
@Autowired
private KafkaTemplate<String, String> kafkaTemplate;

public void sendMessage(String topic, String message) {
    kafkaTemplate.send(topic, message);
    kafkaTemplate.send("user-events", "user.created", message);
}
```

### Kafka Consumer
```java
@KafkaListener(topics = "user-events", groupId = "order-service")
public void consumeUserEvent(ConsumerRecord<String, String> record) {
    String message = record.value();
    // 处理消息
}
```

### RabbitMQ Producer
```java
@Autowired
private RabbitTemplate rabbitTemplate;

public void sendMessage(String exchange, String routingKey, Object message) {
    rabbitTemplate.convertAndSend(exchange, routingKey, message);
    rabbitTemplate.convertAndSend("user.exchange", "user.created", user);
}
```

### RabbitMQ Consumer
```java
@RabbitListener(queues = "order.queue")
public void handleOrder(OrderMessage message) {
    // 处理订单消息
}
```

### RocketMQ Producer
```java
@Autowired
private RocketMQTemplate rocketMQTemplate;

public void sendMessage(String topic, Object message) {
    rocketMQTemplate.syncSend(topic, message);
    rocketMQTemplate.asyncSend("user-topic", message, callback);
}
```

### RocketMQ Consumer
```java
@RocketMQMessageListener(topic = "user-topic", consumerGroup = "order-group")
public class UserConsumer implements RocketMQListener<UserMessage> {
    @Override
    public void onMessage(UserMessage message) {
        // 处理消息
    }
}
```

## 数据库

### MyBatis Mapper
```java
@Mapper
public interface UserMapper {
    @Select("SELECT * FROM users WHERE id = #{id}")
    User findById(Long id);
    
    @Insert("INSERT INTO users(name, email) VALUES(#{name}, #{email})")
    int insert(User user);
}

// 使用
@Autowired
private UserMapper userMapper;
userMapper.findById(1L);
```

### MyBatis-Plus
```java
public interface UserMapper extends BaseMapper<User> {
    // 继承基本CRUD
}

// 使用
userMapper.selectById(1L);
userMapper.insert(user);
userMapper.updateById(user);
userMapper.deleteById(1L);
```

### JPA Repository
```java
@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    List<User> findByStatus(String status);
}

// 使用
@Autowired
private UserRepository userRepository;
userRepository.findById(1L);
userRepository.save(user);
userRepository.delete(user);
```

### JdbcTemplate
```java
@Autowired
private JdbcTemplate jdbcTemplate;

public User findById(Long id) {
    return jdbcTemplate.queryForObject(
        "SELECT * FROM users WHERE id = ?",
        new BeanPropertyRowMapper<>(User.class),
        id
    );
}
```

### MongoDB
```java
@Repository
public interface UserRepository extends MongoRepository<User, String> {
    List<User> findByStatus(String status);
}

// 使用MongoTemplate
@Autowired
private MongoTemplate mongoTemplate;
mongoTemplate.findById(id, User.class);
mongoTemplate.save(user);
```

## 缓存

### Redis
```java
@Autowired
private RedisTemplate<String, Object> redisTemplate;
@Autowired
private StringRedisTemplate stringRedisTemplate;

// 操作
redisTemplate.opsForValue().set("user:1", user);
redisTemplate.opsForValue().get("user:1");
redisTemplate.opsForHash().put("users", "1", user);
redisTemplate.opsForList().leftPush("user:list", user);
```

### Spring Cache
```java
@Cacheable(value = "users", key = "#id")
public User getUserById(Long id) {
    return userRepository.findById(id).orElse(null);
}

@CachePut(value = "users", key = "#user.id")
public User updateUser(User user) {
    return userRepository.save(user);
}

@CacheEvict(value = "users", key = "#id")
public void deleteUser(Long id) {
    userRepository.deleteById(id);
}
```

## Spring注解

### Controller
```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) { }
    
    @PostMapping
    public User createUser(@RequestBody UserRequest request) { }
    
    @PutMapping("/{id}")
    public User updateUser(@PathVariable Long id, @RequestBody UserRequest request) { }
    
    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) { }
}
```

### Service
```java
@Service
public class UserService {
    
    @Transactional
    public User createUser(UserRequest request) { }
    
    @Transactional(readOnly = true)
    public User getUser(Long id) { }
}
```

---

## 常见问题

### Q: 如何识别服务名？

1. **Feign**: 从`@FeignClient(name="service-name")`提取
2. **URL**: 从URL路径提取，如`/api/user-service/users` → `user-service`
3. **配置文件**: 读取`application.yml`中的服务配置

### Q: 如何处理异步调用？

异步调用（如`@Async`、`CompletableFuture`）会标记为异步边，但不会阻塞主流程追踪。

### Q: 如何处理条件调用？

条件分支（如`if-else`）会被追踪，但不会区分条件，会显示所有可能的调用路径。