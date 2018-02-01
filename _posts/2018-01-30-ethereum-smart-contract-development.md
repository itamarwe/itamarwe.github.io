---
layout: post
title:  "Ethereum smart contract development"
comments: true
date:   2018-01-30
categories: personal
---

Recently I worked on issuing an Ethereum token, which is basically
a simple smart contract. Along the process I encountered a few good resources,
frameworks and platforms and gained a few insights that I wanted to share. I also
had trouble finding good resources on how to deploy the smart contracts in production.
There seems to be multiple resources that explain how to test smart contracts,
but less resources on how to actually deploy them to the live Ethereum blockchain.

First, let's start with the smart contract developer's toolbelt - the development
environment.

## Smart contract development toolbelt
There are a couple of types of tools that are necessary for smart contract development.

1. Local test blockchain - In order to test your smart contract operation, and as importantly 
smart contract deployment, you will need a local test blockchain. Local blockchains
imitate the behavior of the Ethereum blockchain, only that they run locally on your
machine, and allow you to restart their state at any time. Usually they create 10
account with balances that you can use to test the functionality of your smart contract.
The most common option I know of is [Ganache](http://truffleframework.com/ganache/).
You can either install the desktop version with the nice UI, or use [ganache-cli]( https://github.com/trufflesuite/ganache-cli) for a command line version.

2. Live blockchain - When you decide to deploy your smart contract on the blockchain
(and also later when you interact with them) you need to have access to a live blockchain
node. Here there are a couple of options:
- [Geth](https://github.com/ethereum/go-ethereum)  - This is the implementation of the Ethereum blockchain node in Go. When you run it you actually run a full Ethereum node. The initial sync of the blockchain might take
a couple of days, since your node will have to download all of the Ethereum blocks
since the creation of the Ethereum blockchain, and will verify all the transactions
one by one. There is also a fast sync, that downloads and verifies only the block headers,
but it is considered less secure, and will still take a considerable amount of time.
- [Parity](https://www.parity.io/) - A local client that allows interacting with the
Ethereum blockchain quickly and easily. It's written to be lightweight and high
performance. It's definitely a good alternative to Geth. It's simpler to install,
doesn't have a long initial sync time. Since it provides a compatible RPC interface,
using it is transparent the other development tools that your using.
- [Infura](https://infura.io/) - Infura allows interacting with the Ethereum blockchain
without the need to install a local client. Once you sign up you get your own unique
link that implements Ethereum's RPC. The advantage is that you don't need to run your
own node or client. The main disadvantage is that you need to trust Infura that
the state of the blockchain that they are providing you is true.

3. [Truffle framework](http://truffleframework.com/) - Truffle is the most popular development framework for Ethereum. It provides tools for compiling, testing, deploying and interacting with smart contracts. You can configure it to work with multiple environments so it can be
used both for testing, working against your local testing blockchain or the Ethereum
testnet, or in production, working against the live Ethereum blockchain.

4. [OpenZeppelin](https://github.com/OpenZeppelin/zeppelin-solidity) - OpenZeppelin is a library for writing secure Smart Contracts on Ethereum. It provides a few basic Solidity (Ethereum's smart contract language) reusable classes. It's very useful when creating your own
contracts and tokens. First, it makes development faster, as many of the common
smart contract features are already implemented and can be used as a boilerplate.
Second, the basic contracts are audited by the entire community and it is therefore
usually more secure to use than writing them yourself.
5. [Web3](https://github.com/ethereum/web3.js/) - Web3 is Ethereum's Javascript
API. It provides a developer-friendly way to interact with Ethereum's RPC API.
Both Truffle and Geth provide a console that you can use to interact with the blockchains.
It's helpful to learn how to use it to interact with your contracts.

## Smart contract development process
Here is how I see the process of smart contract development:
1. Planning - What properties do you want your token or smart contract to have?
It's very useful in this stage to look at examples of other similar smart contracts.
Since many of the smart contracts are open source, you can probably find good references
for almost anything you would like to develop.
2. Development - Write the code for your smart contract.
3. Testing - When it comes to smart contracts, testing is very important. A deployed
contract is like a satellite in space. Once it's deployed it's impossible to modify.
If you have a bug in a deployed contract it will stay there forever. It might make
your contract unusable, or allow [hackers to steal funds](http://hackingdistributed.com/2016/06/18/analysis-of-the-dao-exploit/).
You should first test your contracts locally on a local dev blockchain (e.g. Ganache).
4. Deployment to a public testnet - Once you feel your smart contract is ready, 
it's recommended that you deploy it to a testnet before deploying to production.
Ethereum has a couple of testnets - [Ropsten](https://github.com/ethereum/ropsten), [Kovan](https://github.com/kovan-testnet/proposal) and [Rinkeby](https://www.rinkeby.io/). Deployment on a testnet will give you a good dry run before deploying in production.
Testnets usually have [faucets](https://faucet.rinkeby.io/) - tools that allow you
to get testnet ether for free to test your smart contracts.
5. Deployment in production - After you tested your contract, you can deploy in
production. Remember - once a contract is deployed on the live blockchain, it will
stay there forever. There will be no way to fix it, so make sure it's thoroughly
tested and audited before deployment.

## Gas and Gasprice
Deployment of a s smart contract is a transaction on the Ethereum blockchain. Like
any other transaction, it requires paying fees to the miners.  You need to make
sure that you have enough Ether in the deploying account to cover the fees. The
gas that will be required for the deployment of the contract is determined by the
complexity of the contract. The cost of deploying a complex contract in a reasonable
time can even reach several hundreds of dollars (at the time of writing).
 
### How much Ether do I need?
First, you need to know how much gas is required for the deployment of your contract.
When you test the deployment of your contract with a tools such as Ganache, it will
show you how much gas was consumed by every transaction. This number is not supposed
to change between your local blockchain and the live Ethereum blockchain.

Next, you need to determine a gas price that you are willing to offer the miners.
The miners want to maximize their profit from fees, which is `transaction fee = gas x gasPrice`, and therefore they include transactions with higher gas price first. The higher the
gas price, the faster your transaction will be included in a block (and vice-versa).
The relation between gas price and transaction approval times changes with the load
on the blockchain. There are tools such as [ETH Gas Station](https://ethgasstation.info/)
that allow you to estimate how many blocks you would have to wait before your transaction
will be approved, depending on the gas price you determine. If you have a big complex
contract, but no time pressure, you can set a low gas price, that will make deployment
more affordable. A rule of thumb is to choose a gas price that will get your
transaction approved in less than 50 blocks.

For each transaction, you will also set a gas limit. You need to make sure that:
1. The deployment of your contract will consume less than the gas limit (tested 
  using the local blockchain)
2. You have enough Ether balance in the deploying account to cover 
`gasLimit x gasPrice`. If you don't, the deployment will fail.

## Multi-sig owner account
For some smart contracts, it doesn't matter by which account they were deployed.
Nevertheless, most contracts either provide the entire amount of tokens to the
creator account, or take the creator as the owner of the contract, providing it
with some extra capabilities.

At the very least, the creator account should be based on a strong random seed.
It is even more recommended to deploy from a multi-sig account. Working with a
multi-sig account is slightly more cumbersome, but it is much more secure.

## Useful links
- [The Truffle framework](http://truffleframework.com/docs/)
- [How to create your own crypto-currency with Ethereum](https://www.ethereum.org/token)
- [How to create an ICO with Truffle](https://blog.zeppelin.solutions/how-to-create-token-and-initial-coin-offering-contracts-using-truffle-openzeppelin-1b7a5dae99b6)

Need help building your smart contracts? Contact me at me@itamarweiss.com
