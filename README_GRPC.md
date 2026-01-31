# gRPC Support for Bindu (Issue #67)

This document tracks the implementation of gRPC support for Bindu agents.

## Status: 🚧 In Progress

This is a work-in-progress feature. See [Issue #67](https://github.com/GetBindu/Bindu/issues/67) for the full design document.

## Current Progress

### ✅ Completed
- [x] Protocol Buffer definitions (`.proto` files)
- [x] Basic gRPC server structure
- [x] Protobuf ↔ Pydantic conversion utilities (messages, tasks, push configs, context summaries)
- [x] Core A2AServicer RPCs (SendMessage, GetTask, ListTasks, CancelTask, TaskFeedback, ListContexts, ClearContext, StreamMessage)
- [x] Push notification RPCs
- [x] Unit tests for core RPCs and push notifications

### 🚧 In Progress
- [ ] Generate Python code from `.proto` files (when proto changes)
- [ ] Add gRPC server to BinduApplication
- [ ] Add integration tests
- [ ] Add documentation and examples (deployment, client usage)

### 📋 TODO
- [ ] TLS/SSL support
- [ ] Streaming support
- [ ] Performance benchmarking
- [ ] Client libraries
- [ ] Migration guide

## Getting Started

### Prerequisites

Install gRPC tools:

```bash
pip install grpcio grpcio-tools
```

### Generate Python Code from Proto Files

```bash
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./bindu/grpc \
    --grpc_python_out=./bindu/grpc \
    ./proto/a2a.proto
```

### Running the gRPC Server

```python
from bindu.server.grpc import GrpcServer
from bindu.server.applications import BinduApplication

app = BinduApplication(...)
grpc_server = GrpcServer(app, port=50051)

# Start server
await grpc_server.start()
```

## Push Notification RPCs

The gRPC service mirrors JSON-RPC push notification methods:

- `SetTaskPushNotification`
- `GetTaskPushNotification`
- `ListTaskPushNotifications`
- `DeleteTaskPushNotification`

### Example: Register Push Notifications

```python
import grpc
from bindu.grpc import a2a_pb2, a2a_pb2_grpc

async def register_push_notifications():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        request = a2a_pb2.SetTaskPushNotificationRequest(
            config=a2a_pb2.TaskPushNotificationConfig(
                id="task-uuid",
                push_notification_config=a2a_pb2.PushNotificationConfig(
                    id="push-config-uuid",
                    url="https://example.com/webhook",
                    token="secret-token",
                ),
                long_running=True,
            )
        )
        response = await stub.SetTaskPushNotification(request)
        return response
```

## Core RPCs

The gRPC service mirrors JSON-RPC core task and context methods:

- `ListTasks`
- `CancelTask`
- `TaskFeedback`
- `ListContexts`
- `ClearContext`
- `StreamMessage`

### Example: List Tasks and Cancel One

```python
import grpc
from bindu.grpc import a2a_pb2, a2a_pb2_grpc

async def list_and_cancel_task():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        tasks = await stub.ListTasks(a2a_pb2.ListTasksRequest(limit=10))
        if tasks.tasks:
            await stub.CancelTask(a2a_pb2.TaskIdRequest(task_id=tasks.tasks[0].id))
```

### Example: List Contexts and Clear One

```python
import grpc
from bindu.grpc import a2a_pb2, a2a_pb2_grpc

async def list_and_clear_context():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        contexts = await stub.ListContexts(a2a_pb2.ListContextsRequest(limit=10))
        if contexts.contexts:
            await stub.ClearContext(
                a2a_pb2.ContextIdRequest(context_id=contexts.contexts[0].context_id)
            )
```

### Example: Stream Message Events

```python
import grpc
from bindu.grpc import a2a_pb2, a2a_pb2_grpc

async def stream_message_events():
    async with grpc.aio.insecure_channel("localhost:50051") as channel:
        stub = a2a_pb2_grpc.A2AServiceStub(channel)
        request = a2a_pb2.MessageSendRequest(
            message=a2a_pb2.Message(
                message_id="message-uuid",
                context_id="context-uuid",
                task_id="task-uuid",
                parts=[a2a_pb2.Part(text=a2a_pb2.TextPart(text="Hello"))],
                role="user",
            )
        )
        async for event in stub.StreamMessage(request):
            if event.HasField("status_update"):
                print(event.status_update.status.state)
            elif event.HasField("artifact_update"):
                print(event.artifact_update.artifact.name)
```

## Contributing

We welcome contributions! Areas that need help:

1. **Protocol Converters**: Implement protobuf ↔ Pydantic conversion
2. **Servicer Implementation**: Complete the A2AServicer methods
3. **Testing**: Add unit and integration tests
4. **Documentation**: Improve docs and add examples
5. **Performance**: Optimize gRPC streaming

See [CONTRIBUTING.md](.github/contributing.md) for guidelines.

## References

- [Issue #67](https://github.com/GetBindu/Bindu/issues/67) - Full design document
- [gRPC Python Documentation](https://grpc.io/docs/languages/python/)
- [Protocol Buffers Guide](https://protobuf.dev/getting-started/pythontutorial/)
