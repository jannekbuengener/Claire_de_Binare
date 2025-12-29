$ErrorActionPreference = "Stop"

param(
  [string]$ProtoRoot = "third_party/mexc/websocket-proto",
  [string]$OutDir    = "services/ws/mexc_proto_gen"
)

Write-Host "=== MEXC Protobuf Codegen (D2 Spike) ==="

python -m pip install --upgrade pip | Out-Null
python -m pip install --upgrade protobuf grpcio-tools | Out-Null

$grpcProto = python -c "import os, grpc_tools; print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))"
New-Item -ItemType Directory -Force $OutDir | Out-Null

python -m grpc_tools.protoc `
  -I $ProtoRoot `
  -I $grpcProto `
  --python_out $OutDir `
  "$ProtoRoot/PushDataV3ApiWrapper.proto" `
  "$ProtoRoot/PublicAggreDealsV3Api.proto"

Write-Host "Generated files:" -ForegroundColor Cyan
Get-ChildItem $OutDir -Filter "*_pb2.py" | Select-Object Name
