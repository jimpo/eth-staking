# Ethereum 2.0 Staking Infrastructure

This project contains some of the components I use in my Ethereum 2.0 staking setup.

## Design goals

The starting resource for how to set up an Ethereum 2.0 staking validator is the [Ethereum 2.0 launchpad](https://launchpad.ethereum.org/en/). In order to maximize returns and minimize risk of compromise or accidental slashing events, an operator should want to

1. Protect the cryptographic keys used for voting on blocks
2. Ensure only one validator is running at a time
3. Always run the validator with the database it last exited with to avoid accidentally committing a slashable offense
4. Protect the integrity of the validator process
5. Be online most of the time, but occasional downtime is tolerable
6. BUT ALSO be online whenever enough other validators are offline (weighted by stake) that it affects network liveness, as this would incur severe penalties
7. Have a fallback plan in the event of major bugs in a Ethereum 2.0 implementation or networking failures
8. Have great monitoring and alerting tools

The way I choose to do this is to run the validator on physical hardware on a private network and have it connect to remote servers which run the P2P-connected beacon nodes and monitoring services. The remote nodes can be run on different cloud or VPS providers with full redundancy, requiring coordination only though the validator machine. I as an operator I want some ability to remotely control the validator machine so that it can be left running in a physically secure location, minimizing direct access, but without exposing full remote access to the machine.

To simplify maintenance of the remote nodes, which are to be run with several different infrastructure providers, they are deployed as single instances without fancy coordination or communication and SSH authentication gates all access to the private services they run. The validator, which may run on a private network with NAT, connects to these remote nodes and exposes a control interface through a reverse SSH tunnel.

The benefits this approach has are

- Validator downtime is uncorrelated with outages in major cloud infrastructure providers
- The validator's IP address and thus location are only visible to the remote nodes
- The resource requirements on the validator machine are minimal, so in case of an emergency a new validator instance can be launched until the original is brought back online

The downsides are

- Physical access to the validator is still required for some routine upgrades and maintenance operations, as well as rebooting the validator
- Running several redundant nodes on cloud infrastructure providers can be expensive
- This requires custom software that is maintained by me

## Disclaimers, guarantees, and liability

This project has a bunch of custom software which may be buggy. I take absolutely no responsibility for loss of your funds if you choose to use any of this code.

Only GNU/Linux systems are supported and I have only tested on Ubuntu.

*At the moment, I have no funds staked using this system. When I do, I may update this.*

## Deployment

See the README in the `public-node/` and `supervisor/` directories for further documentation.

## Issues & contact info

If you find a security issue, please contact me. My GPG key fingerprint is `017B 8B03 CCC8 58A5 0B8D  916F E133 7A66 289E D3BD` and the key is on `pgp.mit.edu`. My email is linked to my [GitHub profile](https://github.com/jimpo) and my GPG key.

For other concerns, create a GitHub issue.

## License

Copyright 2021 Jim Posen

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
