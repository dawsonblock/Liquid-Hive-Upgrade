#!/usr/bin/env bash
set -euo pipefail

install_if_missing() {
  local name="$1" check="$2" install="$3"
  if ! bash -lc "$check" >/dev/null 2>&1; then
    echo "Installing $name..."
    bash -lc "$install"
  else
    echo "$name already present"
  fi
}

install_if_missing "cosign" "cosign version" 'curl -sSL https://github.com/sigstore/cosign/releases/download/v2.2.4/cosign-linux-amd64 -o /usr/local/bin/cosign && chmod +x /usr/local/bin/cosign'
install_if_missing "syft" "syft version" 'curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin'
install_if_missing "trivy" "trivy -v" 'sudo apt-get update && sudo apt-get install -y wget && wget -qO- https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo gpg --dearmor -o /usr/share/keyrings/trivy.gpg && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb stable main" | sudo tee /etc/apt/sources.list.d/trivy.list && sudo apt-get update && sudo apt-get install -y trivy'
install_if_missing "helm" "helm version" 'curl -sSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash'
install_if_missing "kind" "kind version" 'curl -sSL https://kind.sigs.k8s.io/dl/v0.23.0/kind-linux-amd64 -o /usr/local/bin/kind && chmod +x /usr/local/bin/kind'
install_if_missing "kubectl" "kubectl version --client" 'curl -sSL https://dl.k8s.io/release/v1.30.2/bin/linux/amd64/kubectl -o /usr/local/bin/kubectl && chmod +x /usr/local/bin/kubectl'
install_if_missing "yq" "yq --version" 'curl -sSL https://github.com/mikefarah/yq/releases/download/v4.44.3/yq_linux_amd64 -o /usr/local/bin/yq && chmod +x /usr/local/bin/yq'

echo "Tools installed."
