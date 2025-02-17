//  **** Rules for badgerDao Care **** 
import "sanity.spec"

methods {
    // constants
    SECONDS_PER_EPOCH() returns(uint256) envfree // => ALWAYS(604800)
    MAX_BPS() returns(uint256) envfree => ALWAYS(10000)

    // other variables
    currentEpoch() returns(uint256) envfree

    // mapping harness getters
    getEpochsStartTimestamp(uint256) returns(uint256) envfree
    getEpochsEndTimestamp(uint256) returns(uint256) envfree
    getPoints(uint256, address, address) returns(uint256) envfree
    getPointsWithdrawn(uint256, address, address, address) returns(uint256) envfree
    getTotalPoints(uint256, address) returns(uint256) envfree
    getLastAccruedTimestamp(uint256, address) returns(uint256) envfree
    getLastUserAccrueTimestamp(uint256, address, address) returns(uint256) envfree
    getLastVaultDeposit(address) returns(uint256) envfree
    getShares(uint256, address, address) returns(uint256) envfree
    getTotalSupply(uint256, address) returns(uint256) envfree
    getRewards(uint256 , address, address) returns(uint256) envfree
    getEligibleRewardsForAmount(uint256 , address, address, address, uint256) returns(uint256) envfree
    getEpoch(uint256) returns (uint256, uint256) envfree

    // methods
    startNextEpoch()
    accrueVault(uint256, address)
    getVaultTimeLeftToAccrue(uint256, address) returns(uint256)
    addRewards(uint256[], address[], address[], uint256[])
    addReward(uint256, address, address, uint256)
    notifyTransfer(address, address, uint256)
    accrueUser(uint256, address, address)
    getUserTimeLeftToAccrue(uint256, address, address) returns(uint256)
    claimRewards(uint256[], address[], address[], address[])
    claimReward(uint256, address, address, address)
    claimBulkTokensOverMultipleEpochs(uint256, uint256, address, address[], address)
    claimBulkTokensOverMultipleEpochsOptimized(uint256, uint256, address, address[])

    handleDeposit(address, address, uint256)
    handleWithdrawal(address, address, uint256)
    handleTransfer(address, address, address, uint256)

    // envfree methods
    getTotalSupplyAtEpoch(uint256, address) returns(uint256, bool) envfree
    getBalanceAtEpoch(uint256, address, address) returns(uint256, bool) envfree
    requireNoDuplicates(address[]) envfree
    min(uint256, uint256) returns(uint256) envfree
    tokenBalanceOf(address, address) returns(uint256) envfree
}


// **** Who can modify which value ****
// points
// totalPoints
// shares
// totalSupply
definition functionAddReward(method f) returns bool =
    f.selector == addReward(uint256, address, address, uint256).selector
    || f.selector == addRewards(uint256[], address[], address[], uint256[]).selector
    ;

definition functionClaim(method f) returns bool =
    f.selector == claimRewards(uint256[], address[], address[], address[]).selector
    || f.selector == claimReward(uint256, address, address, address).selector
    || f.selector == claimBulkTokensOverMultipleEpochs(uint256, uint256, address, address[], address).selector
    || f.selector == claimBulkTokensOverMultipleEpochsOptimized(uint256, uint256, address, address[]).selector
    ;

definition functionTransfer(method f) returns bool =
    f.selector == notifyTransfer(address, address, uint256).selector
    || f.selector == handleDeposit(address, address, uint256).selector
    || f.selector == handleWithdrawal(address, address, uint256).selector
    || f.selector == handleTransfer(address, address, address, uint256).selector
    ;

definition functionUserAccrual(method f) returns bool =
    functionTransfer(f)
    || functionClaim(f)
    || f.selector == accrueUser(uint256, address, address).selector
    ;

definition functionVaultAccrual(method f) returns bool =
    functionClaim(f)
    || f.selector == accrueVault(uint256, address).selector
    // excluding handleTransfer
    || f.selector == notifyTransfer(address, address, uint256).selector
    || f.selector == handleDeposit(address, address, uint256).selector
    || f.selector == handleWithdrawal(address, address, uint256).selector
    ;

// Epoch update
rule invalidValueUpdate_currentEpoch(method f){
    env e; calldataarg args;
    uint256 before_currentEpoch = currentEpoch();
    f(e, args);
    uint256 after_currentEpoch = currentEpoch();
    assert(
        (after_currentEpoch == before_currentEpoch) ||
        (f.selector == startNextEpoch().selector),
        "Currrent epoch updated incorrectly"
    );
}

rule invalidValueUpdate_EpochsStartTimestamp(uint256 epoch, method f){
    env e; calldataarg args;
    uint256 before_EpochsStartTimestamp = getEpochsStartTimestamp(epoch);
    f(e, args);
    uint256 after_EpochsStartTimestamp = getEpochsStartTimestamp(epoch);
    assert(
        (after_EpochsStartTimestamp == before_EpochsStartTimestamp) ||
        (f.selector == startNextEpoch().selector && epoch == currentEpoch()),
        "StartTimeStamp incorrect"
    );
}

rule invalidValueUpdate_EpochsEndTimestamp(uint256 epoch, method f){
    env e; calldataarg args;
    uint256 before_EpochsEndTimestamp = getEpochsEndTimestamp(epoch);
    f(e, args);
    uint256 after_EpochsEndTimestamp = getEpochsEndTimestamp(epoch);
    assert(
        (after_EpochsEndTimestamp == before_EpochsEndTimestamp) 
        || (f.selector == startNextEpoch().selector && epoch == currentEpoch()),
        "EndTimeStamp incorrect"
    );
}

// User points cannot decrease expected optimized claim
rule invalidValueUpdate_Points(uint256 epoch, address vault, address user, method f){
    env e; calldataarg args;
    uint256 before_Points = getPoints(epoch, vault, user);
    f(e, args);
    uint256 after_Points = getPoints(epoch, vault, user);
    assert(
        (after_Points == before_Points) 
        || (
            after_Points == 0 
            && f.selector == claimBulkTokensOverMultipleEpochsOptimized(uint256, uint256, address, address[]).selector
        ) 
        || (
            after_Points > before_Points
            && functionUserAccrual(f)
        ), "User points updated incorrectly"
    );
}

// Total points cannot be decreased
rule invalidValueUpdate_TotalPoints(uint256 epoch, address vault, method f){
    env e; calldataarg args;
    uint256 before_TotalPoints = getTotalPoints(epoch, vault);
    f(e, args);
    uint256 after_TotalPoints = getTotalPoints(epoch, vault);
    assert(
        (after_TotalPoints == before_TotalPoints)
        || (
            after_TotalPoints > before_TotalPoints 
            && getLastAccruedTimestamp(epoch, vault) == e.block.timestamp
            && functionVaultAccrual(f)
        ), "TotalPoints updated incorrectly"
    );
}

// on claim, used points should equal total points of a user
rule invalidValueUpdate_PointsWithdrawn(uint256 epoch, address vault, address user, address token, method f){
    env e; calldataarg args;
    uint256 before_PointsWithdrawn = getPointsWithdrawn(epoch, vault, user, token);
    f(e, args);
    uint256 after_PointsWithdrawn = getPointsWithdrawn(epoch, vault, user, token);
    assert(
        (after_PointsWithdrawn == before_PointsWithdrawn)
        || (
            (functionClaim(f) 
            && after_PointsWithdrawn == getPoints(epoch, vault, user)
            )
        ), "Value updated in wrong function"
    );
}


// Timestamp can only be updated in accrueVault, and set equal to block.timestamp
rule invalidValueUpdate_LastAccruedTimestamp(uint256 epoch, address vault, method f){
    env e; calldataarg args;
    uint256 before_LastAccruedTimestamp = getLastAccruedTimestamp(epoch, vault);
    f(e, args);
    uint256 after_LastAccruedTimestamp = getLastAccruedTimestamp(epoch, vault);
    assert(
        (after_LastAccruedTimestamp == before_LastAccruedTimestamp)
        || (
            (after_LastAccruedTimestamp == e.block.timestamp)    
            && functionVaultAccrual(f)
        ), "Incorrect update"
    );
}

// Timestamp can only be updated in accrueUser, and set equal to block.timestamp
rule invalidValueUpdate_LastUserAccrueTimestamp(uint256 epoch, address vault, address user, method f){
    env e; calldataarg args;
    uint256 before_LastUserAccrueTimestamp = getLastUserAccrueTimestamp(epoch, vault, user);
    f(e, args);
    uint256 after_LastUserAccrueTimestamp = getLastUserAccrueTimestamp(epoch, vault, user);
    assert(
        (after_LastUserAccrueTimestamp == before_LastUserAccrueTimestamp)
        || (
            (after_LastUserAccrueTimestamp == e.block.timestamp)    
            && functionUserAccrual(f)
        ),"Incorrect update"
    );
}

// Unused variable
rule invalidValueUpdate_LastVaultDeposit(uint256 epoch, address vault, address user, method f){
    env e; calldataarg args;
    uint256 before_LastVaultDeposit = getLastVaultDeposit(user);
    f(e, args);
    uint256 after_LastVaultDeposit = getLastVaultDeposit(user);
    assert(
        (after_LastVaultDeposit == before_LastVaultDeposit),
        "Last Vault deposit value should never change since it wasn't used"
    );
}

// Only notify transfer can update a user's shares
rule invalidValueUpdate_Shares(uint256 epoch, address vault, address user, method f){
    env e; calldataarg args;
    uint256 before_Shares = getShares(epoch, vault, user);
    f(e, args);
    uint256 after_Shares = getShares(epoch, vault, user);
    assert(
        (after_Shares == before_Shares)
        || (functionTransfer(f)),
        "Shares updated in wrong function"
    );
}

// Only notifyTransfer can change totalSupply
rule invalidValueUpdate_TotalSupply(uint256 epoch, address vault, method f){
    env e; calldataarg args;
    uint256 before_TotalSupply = getTotalSupply(epoch, vault);
    f(e, args);
    uint256 after_TotalSupply = getTotalSupply(epoch, vault);
    assert(
        (after_TotalSupply == before_TotalSupply)
        || (
            functionTransfer(f) 
        ), "Supply updated in wrong function"
    );
}

// Reward can only be increased
// The balance of vault should increase by the same amount
rule invalidValueUpdate_Rewards(uint256 epoch, address vault, address token, method f){
    env e; calldataarg args;
    uint256 before_Rewards = getRewards(epoch, vault, token);
    uint256 before_VaultBalance = tokenBalanceOf(token, vault);
    f(e, args);
    uint256 after_Rewards = getRewards(epoch, vault, token);
    uint256 after_VaultBalance = tokenBalanceOf(token, vault);
    assert(
        (after_Rewards == before_Rewards)
        || (
            functionAddReward(f) 
            && after_VaultBalance >= before_VaultBalance
            // @note : VaultBalance isn't getting updated properly, due to safeTransferFrom call
            // TODO : Find a fix so vaultBalance updates correctly
            && (after_VaultBalance - before_VaultBalance == after_Rewards - before_Rewards) ),
        "Invalid update to rewards"
    );
}

// User shouldn't be able to reduce the balance of someone else
// Only valid functions can change token balance
rule invalidValueUpdate_tokenBalanceOf(address token, address user, method f){
    env e; calldataarg args;
    uint256 before_tokenBalanceOf = tokenBalanceOf(token, user);
    f(e, args);
    uint256 after_tokenBalanceOf = tokenBalanceOf(token, user);
    assert(
        (after_tokenBalanceOf == before_tokenBalanceOf) 
        || functionClaim(f)
        || (
            functionAddReward(f) 
            && (user != e.msg.sender => after_tokenBalanceOf >= before_tokenBalanceOf)
        ), "Token balance updated incorrectly"
    );
}