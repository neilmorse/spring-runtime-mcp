# ADR 005: 仅连接回环地址

**状态**：已接受

**日期**：2024-11

---

## Context（上下文）

MCP 服务需要连接 Spring Boot 应用读取 Actuator 数据。关键安全考量：

1. **SSRF 风险**：恶意输入可能导致连接内网或外网资源
2. **凭据泄露**：Bearer 令牌不应发送到外部服务器
3. **数据来源可信**：只应读取本地开发/测试环境
4. **编码助手权限**：不应访问生产或远程环境

现有威胁：
- 编码助手可能被诱导连接攻击者控制的服务器
- 本地 DNS 劫持或 hosts 文件篡改
- 跨网络边界的意外连接
- 通过 MCP 工具进行内网扫描

## Decision（决策）

**仅允许连接到回环地址**，拒绝所有其他目标：

### 1. 允许的地址范围

- **IPv4**：`127.0.0.0/8`（127.0.0.1 - 127.255.255.255）
- **IPv6**：`::1`

### 2. DNS 解析后检查

```python
# 1. 解析域名到 IP
resolved_ip = socket.getaddrinfo(host, port)

# 2. 验证解析后的 IP 在回环范围内
if not is_loopback(resolved_ip):
    raise ConnectionRefusedError("LOOPBACK_ONLY")
```

### 3. 连接使用数字 IP

- 解析后使用数字 IP 建立连接
- 避免二次 DNS 解析（TOCTOU 攻击）

### 4. HTTPS peer 验证

- HTTPS 连接验证 peer 地址仍在回环范围
- 使用默认 TLS 验证（不允许自签名）

## Consequences（后果）

### 正面影响

1. **SSRF 防护**
   - 无法连接内网（192.168.x.x、10.x.x.x）
   - 无法连接外网（公网 IP）
   - DNS 劫持无效（解析后仍验证）

2. **凭据安全**
   - Bearer 令牌只发送到本地
   - 无泄露到外部服务器风险

3. **使用场景明确**
   - 仅限本地开发/测试
   - 不支持远程诊断（设计意图）

4. **审计简单**
   - 连接日志只包含 127.0.0.1 或 ::1
   - 异常连接容易识别

### 负面影响

1. **无法诊断远程环境**
   - 不支持连接测试/预发布环境
   - 无法远程排查生产问题

2. **容器/VM 场景受限**
   - 容器内应用需要暴露到宿主机回环
   - VM 需要端口转发

3. **多机部署不支持**
   - 无法连接同网络的其他机器
   - 分布式应用只能逐个机器诊断

### 缓解措施

1. **文档明确说明**
   - README "Boundaries" 章节强调回环限制
   - 提供容器/VM 端口转发示例

2. **错误提示清晰**
   - 非回环地址返回明确错误
   - 提供本地端口转发建议

3. **本地代理方案**
   - 推荐使用 SSH 隧道转发远程端口
   - 保持 MCP 服务只连本地

## 替代方案

### 方案 A：允许配置白名单

```bash
--allowed-targets 192.168.1.100,10.0.0.50
```

- **优点**：支持内网诊断
- **缺点**：增加复杂度，SSRF 风险重现，凭据可能泄露

### 方案 B：允许所有地址

- **优点**：无连接限制
- **缺点**：SSRF 高风险，凭据泄露风险，违背设计初衷

### 方案 C：仅允许 localhost

- **优点**：更严格（只允许 127.0.0.1）
- **缺点**：无法使用 127.0.0.x 的其他地址，某些测试场景受限

### 决策理由

选择回环范围是因为：
- **安全优先**：SSRF 和凭据泄露是严重风险
- **使用场景清晰**：MCP 设计用于本地开发，不是生产诊断工具
- **远程诊断有替代方案**：SSH 隧道、Kubernetes port-forward
- **简单可验证**：回环检查简单高效

## 相关决策

- [ADR 004: 配置诊断默认关闭](004-config-diagnostics-opt-in.md) - 另一层安全边界

## 实现细节

- 地址检查：`src/spring_runtime_mcp/transport/actuator_http.py`
- DNS 解析：标准库 `socket.getaddrinfo`
- 回环验证：`ipaddress.IPv4Address.is_loopback` / `IPv6Address.is_loopback`

### 检查逻辑

```python
def verify_loopback_only(host: str, port: int) -> tuple[str, int]:
    # 解析域名
    results = socket.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    
    for family, _, _, _, sockaddr in results:
        ip_str = sockaddr[0]
        
        # 验证是回环地址
        if family == socket.AF_INET:
            ip = ipaddress.IPv4Address(ip_str)
            if not ip.is_loopback:
                raise ConnectionRefusedError("LOOPBACK_ONLY")
        elif family == socket.AF_INET6:
            ip = ipaddress.IPv6Address(ip_str)
            if not ip.is_loopback:
                raise ConnectionRefusedError("LOOPBACK_ONLY")
    
    # 返回数字 IP 用于连接
    return results[0][4][0], port
```

## 远程诊断替代方案

### 方案 1：SSH 隧道

```bash
# 将远程 18081 端口转发到本地 18081
ssh -L 18081:127.0.0.1:18081 user@remote-server

# MCP 连接本地
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081
```

### 方案 2：Kubernetes port-forward

```bash
# 将 Pod 端口转发到本地
kubectl port-forward pod/my-app-pod 18081:8080

# MCP 连接本地
uvx spring-runtime-mcp --base-url http://127.0.0.1:18081
```

### 方案 3：容器网络

```yaml
# docker-compose.yml
services:
  app:
    ports:
      - "127.0.0.1:18081:8080"  # 只暴露到宿主机回环
```

## 安全审计

定期检查：
- 连接日志中是否有非回环地址尝试
- DNS 解析是否被劫持（hosts 文件）
- 代码中的回环检查是否被绕过

## 例外情况

**无例外**。即使操作者明确请求，也不允许连接非回环地址。远程诊断应使用端口转发。
