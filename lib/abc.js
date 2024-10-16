
(function(){
    document.addEventListener('DOMContentLoaded', function() {
        const contentArea = document.getElementById('content');
        let lastContent = contentArea.value;

        // 自动保存内容每秒检测一次
        setInterval(function() {
            const currentContent = contentArea.value;
            if (currentContent !== lastContent) {
                fetch('/update/' + encodeURIComponent(identifier), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 'content': currentContent })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        console.log('Update successful');
                        lastContent = currentContent;
                        showSaveSuccess();
                    } else {
                        alert(data.message);
                    }
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
            }
        }, 1000); // 每秒检测一次

        // 处理 Share 按钮点击
        const shareButton = document.getElementById('shareButton');
        if (shareButton) {
            shareButton.addEventListener('click', function() {
                fetch('/create_share/' + encodeURIComponent(identifier), {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const shareUrl = window.location.origin + data.share_url;
                        window.open(shareUrl, '_blank');
                    } else {
                        alert(data.message);
                    }
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
            });
        }

        // 处理 Share (Burn after read) 按钮点击
        const burnShareButton = document.getElementById('burnShareButton');
        if (burnShareButton) {
            burnShareButton.addEventListener('click', function() {
                fetch('/create_burn/' + encodeURIComponent(identifier), {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        const burnUrl = window.location.origin + data.burn_url;
                        showBurnLink(burnUrl);
                    } else {
                        alert(data.message);
                    }
                })
                .catch((error) => {
                    console.error('Error:', error);
                });
            });
        }

        // 显示保存成功的提示
        let saveSuccessTimeout = null;
        function showSaveSuccess() {
            const msg = document.getElementById('saveSuccess');
            if (!msg) return;
            msg.style.opacity = 1;
            if (saveSuccessTimeout) {
                clearTimeout(saveSuccessTimeout);
            }
            // 1秒后开始淡出
            saveSuccessTimeout = setTimeout(() => {
                msg.style.opacity = 0;
            }, 1000); // 1秒显示
        }

        // 显示烧毁链接的弹窗
        function showBurnLink(url) {
            const modal = document.getElementById('burnModal');
            const burnLink = document.getElementById('burnLink');
            burnLink.href = url;
            burnLink.textContent = url;
            modal.style.display = 'block';
        }

        // 处理弹窗关闭
        const closeModal = document.getElementsByClassName('close')[0];
        if (closeModal) {
            closeModal.onclick = function() {
                const modal = document.getElementById('burnModal');
                modal.style.display = 'none';
            }
        }

        // 点击弹窗外部关闭弹窗
        window.onclick = function(event) {
            const modal = document.getElementById('burnModal');
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        }
    });
})();
