param(
  [string]$Region  = "us-west-2",
  [string]$Cluster = "icevision-cluster",
  [string]$Service = "icevision-service",
  [string]$AlbName = "icevision-alb",
  [string]$TgName  = "icevision-tg"
)

# 1) Scale service to 0 and wait
aws ecs update-service --cluster $Cluster --service $Service --desired-count 0 --region $Region | Out-Null
do {
  $svc = aws ecs describe-services --cluster $Cluster --services $Service --region $Region | ConvertFrom-Json
  $running = $svc.services[0].runningCount
  Start-Sleep 3
} while ($running -gt 0)

# 2) Delete ALB (listeners go with it) and wait gone
$albArn = (aws elbv2 describe-load-balancers --names $AlbName --region $Region 2>$null | ConvertFrom-Json).LoadBalancers[0].LoadBalancerArn
if ($albArn) {
  aws elbv2 delete-load-balancer --load-balancer-arn $albArn --region $Region | Out-Null
  do {
    Start-Sleep 3
    $albGone = -not (aws elbv2 describe-load-balancers --load-balancer-arns $albArn --region $Region 2>$null)
  } until ($albGone)
}

# 3) Wait until TG is no longer attached to any LB, then delete it
$tg = aws elbv2 describe-target-groups --names $TgName --region $Region 2>$null | ConvertFrom-Json
if ($tg) {
  $tgArn = $tg.TargetGroups[0].TargetGroupArn
  # Poll until LoadBalancerArns is empty
  for ($i=0; $i -lt 60; $i++) {
    $tg = aws elbv2 describe-target-groups --target-group-arns $tgArn --region $Region 2>$null | ConvertFrom-Json
    if (-not $tg) { break }
    $attached = $tg.TargetGroups[0].LoadBalancerArns
    if (-not $attached -or $attached.Count -eq 0) { break }
    Start-Sleep 5
  }
  # Try-delete with a couple retries (handles residual “in use”)
  for ($j=0; $j -lt 5; $j++) {
    $err = $null
    try {
      aws elbv2 delete-target-group --target-group-arn $tgArn --region $Region | Out-Null
      $err = $null; break
    } catch { $err = $_; Start-Sleep 4 }
  }
  if ($err) { Write-Host "Paused. TG still detaching (will disappear shortly): $tgArn" ; exit 0 }
}

Write-Host "Paused. Service=0; ALB and TG removed."
