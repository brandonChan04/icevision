param(
  [string]$Region        = "us-west-2",
  [string]$Cluster       = "icevision-cluster",
  [string]$Service       = "icevision-service",
  [string]$AlbName       = "icevision-alb",
  [string]$TgName        = "icevision-tg",
  [int]$ContainerPort    = 8000,
  [string]$AlbSgName     = "icevision-alb-sg",
  [string]$TaskSgName    = "icevision-task-sg"
)

# Ensure log group exists (safe if already there)
aws logs create-log-group --log-group-name /ecs/icevision-api --region $Region 2>$null

# Default VPC + two subnets
$defaultVpc = (aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region $Region | ConvertFrom-Json).Vpcs[0].VpcId
if (-not $defaultVpc) { aws ec2 create-default-vpc --region $Region | Out-Null; $defaultVpc = (aws ec2 describe-vpcs --filters Name=isDefault,Values=true --region $Region | ConvertFrom-Json).Vpcs[0].VpcId }
$subs = (aws ec2 describe-subnets --filters Name=vpc-id,Values=$defaultVpc --region $Region | ConvertFrom-Json).Subnets | Select-Object -ExpandProperty SubnetId
$subnet1 = $subs[0]; $subnet2 = $subs[1]

# Security groups
$albSg = (aws ec2 describe-security-groups --filters Name=vpc-id,Values=$defaultVpc Name=group-name,Values=$AlbSgName --region $Region 2>$null | ConvertFrom-Json).SecurityGroups[0].GroupId
if (-not $albSg) {
  $albSg = (aws ec2 create-security-group --group-name $AlbSgName --description "ALB SG" --vpc-id $defaultVpc --region $Region | ConvertFrom-Json).GroupId
  aws ec2 authorize-security-group-ingress --group-id $albSg --protocol tcp --port 80 --cidr 0.0.0.0/0 --region $Region | Out-Null
}
$taskSg = (aws ec2 describe-security-groups --filters Name=vpc-id,Values=$defaultVpc Name=group-name,Values=$TaskSgName --region $Region 2>$null | ConvertFrom-Json).SecurityGroups[0].GroupId
if (-not $taskSg) {
  $taskSg = (aws ec2 create-security-group --group-name $TaskSgName --description "ECS tasks SG" --vpc-id $defaultVpc --region $Region | ConvertFrom-Json).GroupId
  aws ec2 authorize-security-group-ingress --group-id $taskSg --protocol tcp --port $ContainerPort --source-group $albSg --region $Region | Out-Null
}

# ALB
$albArn = (aws elbv2 create-load-balancer --name $AlbName --type application --subnets $subnet1 $subnet2 --security-groups $albSg --region $Region | ConvertFrom-Json).LoadBalancers[0].LoadBalancerArn
aws elbv2 wait load-balancer-available --load-balancer-arns $albArn --region $Region

# TG (create if missing)
$tgDescribe = aws elbv2 describe-target-groups --names $TgName --region $Region 2>$null
if ($tgDescribe) {
  $tgArn = ($tgDescribe | ConvertFrom-Json).TargetGroups[0].TargetGroupArn
}
if (-not $tgArn) {
  $tgArn = (aws elbv2 create-target-group --name $TgName --protocol HTTP --port $ContainerPort --vpc-id $defaultVpc --target-type ip --health-check-path "/docs" --region $Region | ConvertFrom-Json).TargetGroups[0].TargetGroupArn
}

# Listener :80 -> TG
aws elbv2 create-listener --load-balancer-arn $albArn --protocol HTTP --port 80 --default-actions Type=forward,TargetGroupArn=$tgArn --region $Region | Out-Null

# Ensure service uses this TG ARN (important if TG was deleted & recreated)
aws ecs update-service --cluster $Cluster --service $Service `
  --load-balancers "targetGroupArn=$tgArn,containerName=icevision,containerPort=$ContainerPort" `
  --region $Region | Out-Null

# Start one task & wait healthy
aws ecs update-service --cluster $Cluster --service $Service --desired-count 1 --force-new-deployment --region $Region | Out-Null
do {
  Start-Sleep -Seconds 3
  $states = aws elbv2 describe-target-health --target-group-arn $tgArn --region $Region | ConvertFrom-Json
  $healthy = ($states.TargetHealthDescriptions | ForEach-Object { $_.TargetHealth.State }) -contains "healthy"
} until ($healthy)

$albDns = (aws elbv2 describe-load-balancers --load-balancer-arns $albArn --region $Region | ConvertFrom-Json).LoadBalancers[0].DNSName
Write-Host ":iconicintern Host ready at :goforit : http://$albDns/docs"
