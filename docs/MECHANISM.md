# Mechanism

This document describes the mechanism of **AFB**. There are two main components in **AFB**:

- `Manufacturer`: Collection of factories of a class.
- `Broker`: Collection of `Manufacturer`s.

## Manufacturer

A `Manufacturer` is a collection of factories of a class. It holds the following details for each registrant:

- `factory`: The function for the target class object creation.
- `signature`: Type and description for each argument.
- `descriptions`: Descriptions on the object returned from the factory.

The handling of each object creation request involves the following steps:

1. Retrieves the specified factory with its signature.
2. Prepares the factory arguments.
3. Performs the factory call and returns the resulting object.

Each factory is keyed by a `str` name given at its registration. Such name is used for its retrieval in step 1.

Step 2 prepares the arguments for the function call based on the given ones. For each argument, the `Manufacturer` either:

1. Includes the given value as is, if it is an instance of the expected type; Or
2. Makes a request for object creation via `Broker` (see below).

Step 3 calls the target factory with the above prepared parameters and returns the result.

## Broker

A `Broker` is a collection of `Manufacturer`s. Each `Manufacturer` is responsible for object instantiation for a particular class.

Like the `Manufacturer`, a `Broker` also accepts object creation requests. In constrast to `Manufacturer`, `Broker` delegates the instantiation to the responsible `Manufacturer` for the target type.


The handling of each object creation request of a particular type involves the following steps:

1. Retrieves the `Manufacturer` of the target type.
2. Passes the request to it.
3. Returns the result.

A network of `Manufacturer`s can be constructed through registration to a single `Broker`. The registered `Manufacturer`s will be visible to the `Broker` for object creation request delegation. The argument preparation step in `Manufacturer` relies on `Broker` to forward the request to the responsible one for object instantiation. The object instantiation process through this network is effectively a Depth First Traversal of the dependency tree of the involved factories.
