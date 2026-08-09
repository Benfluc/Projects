# TABLE CODES


                      ProductPairs = 
            FILTER(
                ADDCOLUMNS(
                    GENERATE(
                        'CustomerProducts',
                        SELECTCOLUMNS(
                            FILTER(
                                'CustomerProducts',
                                [Customer] = EARLIER([Customer]) &&
                                [Product] <> EARLIER([Product])
                            ),
                            "AssociatedProduct", [Product]
                        )
                    ),
                    "BaseProduct", [Product]
                ),
                [BaseProduct] <> [AssociatedProduct]
            )




                            ProductPairsCount = 
                SUMMARIZE(
                    'ProductPairs',
                    'ProductPairs'[BaseProduct],
                    'ProductPairs'[AssociatedProduct],
                    "TimesBoughtTogether", COUNTROWS('ProductPairs')
                )



                        CustomerProducts = 
        DISTINCT(
            SELECTCOLUMNS(
                'Sales_Store',
                "Customer", 'Sales_Store'[Customer Name],
                "Product", 'Sales_Store'[Product Name]
            )
        )
