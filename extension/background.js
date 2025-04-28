chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
      id: "scanLink",
      title: "Scan Link in Safe Mode",
      contexts: ["link"]
    });
  });
  
  chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === "scanLink") {
      console.log("Context menu clicked. Sending URL:", info.linkUrl);
      fetch('http://localhost:8000/analyze_link', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ url: info.linkUrl })
      })
      .then(response => {
          console.log("Fetch response received:", response);
          if (!response.ok) {
            console.error("Fetch failed with status:", response.status);
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then(data => {
        console.log("Response data (JSON parsed):", data);
        console.log(`Scan Result: ${data.status}`);
        // Store the result for the popup
        chrome.storage.local.set({ lastScanResult: data }, () => {
            console.log("Scan result saved to storage.");
            // Automatically open the popup window after successful scan
            chrome.windows.create({
                url: "popup.html",
                type: "popup",
                width: 400, // Adjust size as needed
                height: 250 // Reduce default height
            });
        });
      })
      .catch(err => {
        console.error("An error occurred:", err);
        // Also store error state for the popup
        chrome.storage.local.set({ 
            lastScanResult: { 
                status: 'error', 
                details: err.message || "Unknown fetch error",
                analysis: { suspicious: true, reasons: ["Backend communication failed"] }
            }
        });
      });
    }
  });