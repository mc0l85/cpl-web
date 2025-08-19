#Requires -Modules AzureAD, ActiveDirectory

<#
.SYNOPSIS
    Scans an Azure AD group, builds the full Active Directory management chain for each member, 
    and then prompts the user with a "Save As" dialog to export the data to a CSV file.

.DESCRIPTION
    This script performs the following actions:
    1. Checks for required PowerShell modules and network connectivity.
    2. Fetches all user data from the on-premises Active Directory in a single, efficient batch to build an in-memory map.
    3. Connects to Azure Active Directory.
    4. Retrieves all members of the 'AAD-AZC-Corp-Lic-M365-Copilot-DIRECT' group.
    5. For each group member, it uses the in-memory map to instantly build their full manager hierarchy and retrieve their city, company, and department.
    6. After processing, it opens a graphical "Save As" dialog for the user to choose the save location and filename for the CSV report.

.NOTES
    - Ensure you have the AzureAD and ActiveDirectory PowerShell modules installed.
    - You will need appropriate permissions to read from both Azure AD and your on-premises Active Directory.
    - The script is configured for the domain 'ad.corpnet4.net'. You may need to change this to your domain.
    - This script will open a GUI window and is intended for interactive use on a desktop environment.
#>

# --- Script Configuration ---
$azureAdGroupName = "AAD-AZC-Corp-Lic-M365-Copilot-DIRECT"
$adDomain = "ad.corpnet4.net"
$azureConnectionEstablished = $false

# --- Pre-flight Checks ---
Write-Host "Checking for required PowerShell modules..."
if (-not (Get-Module -ListAvailable -Name AzureAD)) {
    Write-Error "The AzureAD module is not installed. Please run 'Install-Module AzureAD' and try again."
    exit
}
if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "The ActiveDirectory module is not installed. Please ensure Remote Server Administration Tools (RSAT) for AD DS is installed."
    exit
}
Write-Host "Required modules are present."

# --- Optimized Function to Get Manager Chain from In-Memory Map ---
function Get-ManagerChainFromMap {
    param(
        [string]$UserPrincipalName,
        [hashtable]$UpnToUserMap,
        [hashtable]$DnToUserMap
    )

    $managerChain = [System.Collections.ArrayList]@()
    try {
        if ($UpnToUserMap.ContainsKey($UserPrincipalName)) {
            $user = $UpnToUserMap[$UserPrincipalName]
            $currentManagerDn = $user.Manager

            while ($null -ne $currentManagerDn) {
                if ($DnToUserMap.ContainsKey($currentManagerDn)) {
                    $managerUser = $DnToUserMap[$currentManagerDn]
                    $managerChain.Add($managerUser.DisplayName) | Out-Null
                    $currentManagerDn = $managerUser.Manager
                } else {
                    $currentManagerDn = $null
                }
            }
        } else {
            Write-Warning "User with UPN '$UserPrincipalName' could not be found in the pre-loaded Active Directory data."
        }
    }
    catch {
        Write-Warning "An error occurred while processing the manager chain for UPN '$UserPrincipalName' from the in-memory map. Error: $($_.Exception.Message)"
    }
    return $managerChain
}

# --- Main Script ---
try {
    # --- Performance Optimization: Pre-load all AD user data ---
    Write-Host "Optimizing for performance by pre-loading all user data from Active Directory..."
    $dnToUserMap = @{}
    $upnToUserMap = @{}
    try {
        # Change: Added Company and Department to the list of properties to fetch.
        $allAdUsers = Get-ADUser -Filter * -Server $adDomain -Properties UserPrincipalName, DisplayName, Manager, l, Company, Department -ErrorAction Stop
        foreach ($user in $allAdUsers) {
            $dnToUserMap[$user.DistinguishedName] = $user
            if ($user.UserPrincipalName) {
                $upnToUserMap[$user.UserPrincipalName] = $user
            }
        }
        Write-Host "Successfully loaded $($allAdUsers.Count) users into the in-memory map." -ForegroundColor Green
    } catch {
        Write-Error "Failed to pre-load user data from Active Directory. Please check permissions and connectivity to '$adDomain'. Error: $($_.Exception.Message)"
        exit
    }
    
    # --- Step 1: Connect to Azure AD and get group members ---
    try {
        Write-Host "Testing network connectivity to Azure AD endpoint..."
        if (-not (Test-NetConnection -ComputerName graph.windows.net -Port 443 -InformationLevel Quiet)) {
             throw "Network connectivity test failed. Cannot reach graph.windows.net on port 443. Please check your firewall and proxy settings."
        }
        Write-Host "Network connectivity test passed." -ForegroundColor Green

        Write-Host "Connecting to Azure Active Directory..."
        Connect-AzureAD -ErrorAction Stop
        $azureConnectionEstablished = $true
        Write-Host "Successfully connected to Azure AD."
    }
    catch {
        Write-Error "Failed to connect to Azure AD. The specific error was: $($_.Exception.Message)"
        exit
    }

    $groupMembers = $null
    $maxRetries = 3
    $retryDelaySeconds = 5
    for ($attempt = 1; $attempt -le $maxRetries; $attempt++) {
        try {
            Write-Host "Attempting to retrieve group members (Attempt ${attempt} of ${maxRetries})..."
            $group = Get-AzureADGroup -Filter "DisplayName eq '$azureAdGroupName'" -ErrorAction Stop
            if (-not $group) {
                throw "Azure AD group '$azureAdGroupName' not found."
            }
            $groupMembers = Get-AzureADGroupMember -ObjectId $group.ObjectId -All $true -ErrorAction Stop
            Write-Host "Successfully retrieved group members." -ForegroundColor Green
            break 
        }
        catch {
            Write-Warning "An error occurred while retrieving group members: $($_.Exception.Message)"
            if ($attempt -lt $maxRetries) {
                Write-Warning "Retrying in $retryDelaySeconds seconds..."
                Start-Sleep -Seconds $retryDelaySeconds
            } else {
                throw
            }
        }
    }
    
    if (-not $groupMembers) {
        Write-Warning "No members were ultimately found in the Azure AD group '$azureAdGroupName' after all attempts."
    }

    if ($groupMembers) {
        # --- Step 2: Build the user data for export using the in-memory maps ---
        $exportData = [System.Collections.ArrayList]@()
        Write-Host "Building user data using the in-memory map..."
        
        $totalUsers = $groupMembers.Count
        $processedUsers = 0

        foreach ($member in $groupMembers) {
            $processedUsers++
            Write-Progress -Activity "Processing Users" -Status "Processing user ${processedUsers} of ${totalUsers}: $($member.DisplayName)" -PercentComplete (($processedUsers / $totalUsers) * 100)

            $upn = $member.UserPrincipalName
            $managerChain = Get-ManagerChainFromMap -UserPrincipalName $upn -UpnToUserMap $upnToUserMap -DnToUserMap $dnToUserMap
            
            # Change: Initialize all variables that will be populated from the map.
            $city = $null
            $company = $null
            $department = $null
            if ($upnToUserMap.ContainsKey($upn)) {
                $adUser = $upnToUserMap[$upn]
                $city = $adUser.l
                $company = $adUser.Company
                $department = $adUser.Department
            }
    
            # Change: Add the new properties to the object being exported.
            $exportData.Add([PSCustomObject]@{
                UserPrincipalName = $upn
                Company           = $company
                Department        = $department
                City              = $city
                ManagerLine       = ($managerChain -join ' -> ')
            }) | Out-Null
        }
    
        Write-Host "Successfully built the user data." -ForegroundColor Green
    
        # --- Step 3: Prompt user with Save As dialog and export data ---
        if ($exportData.Count -gt 0) {
            try {
                # Add the required .NET assembly for the Save File Dialog
                Add-Type -AssemblyName System.Windows.Forms
                $saveFileDialog = New-Object System.Windows.Forms.SaveFileDialog
                $saveFileDialog.Title = "Save Manager Report"
                $saveFileDialog.Filter = "CSV files (*.csv)|*.csv|All files (*.*)|*.*"
                $saveFileDialog.InitialDirectory = [Environment]::GetFolderPath('Desktop')
                $saveFileDialog.FileName = "ManagerReport.csv"

                if ($saveFileDialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
                    $outputCsvPath = $saveFileDialog.FileName
                    Write-Host "Exporting data to CSV file at '$outputCsvPath'..." -ForegroundColor Cyan
                    $exportData | Export-Csv -Path $outputCsvPath -NoTypeInformation -Encoding UTF8 -ErrorAction Stop
                    Write-Host "Export complete." -ForegroundColor Green
                } else {
                    Write-Host "File export was canceled by the user." -ForegroundColor Yellow
                }
            } catch {
                Write-Error "An error occurred with the Save File dialog or export process. Error: $($_.Exception.Message)"
            }
        } else {
            Write-Warning "No user data was generated, so there is nothing to export."
        }
    }
}
catch {
    Write-Error "A critical error occurred: $($_.Exception.Message)"
}
finally {
    if ($azureConnectionEstablished) {
        Write-Host "`nDisconnecting from Azure AD."
        Disconnect-AzureAD
    }
}
