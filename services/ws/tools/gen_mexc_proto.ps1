param(
  [string]$ProtoRoot = "third_party/mexc/websocket-proto",
  [string]$OutDir    = "services/ws/mexc_proto_gen"
)

$ErrorActionPreference = "Stop"

Write-Host "=== MEXC Protobuf Codegen (ALL protos, D2) ==="

python -m pip install --upgrade pip | Out-Null
python -m pip install --upgrade protobuf grpcio-tools | Out-Null

$grpcProto = python -c "import os, grpc_tools; print(os.path.join(os.path.dirname(grpc_tools.__file__), '_proto'))"

New-Item -ItemType Directory -Force $OutDir | Out-Null

$protos = Get-ChildItem $ProtoRoot -Filter "*.proto" | Sort-Object Name
Write-Host ("Found {0} proto files" -f $protos.Count)
foreach ($p in $protos) {
  python -m grpc_tools.protoc `
    -I $ProtoRoot `
    -I $grpcProto `
    --python_out $OutDir `
    "$ProtoRoot/$($p.Name)"
}

Write-Host "Generated files:" -ForegroundColor Cyan
Get-ChildItem $OutDir -Filter "*_pb2.py" | Select-Object Name
