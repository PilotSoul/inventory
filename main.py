from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import redis

app = FastAPI()

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*']
)


class Product(BaseModel):
    name: str
    price: float
    quantity: int


@app.get("/product/all")
async def get_products(limit: int = Query(default=10, le=100)):
    products = []
    product_keys = redis_client.keys("product:*")
    product_keys = product_keys[:limit]
    for key in product_keys:
        product_data = redis_client.hgetall(key)
        if product_data:
            product_dict = {"id": key.split(":")[-1], **product_data}
            products.append(product_dict)
    return products


@app.get("/product/{pk}")
def get_product(pk: str):
    try:
        product_id = f"product:{pk}"
        product = redis_client.hgetall(product_id)
        if product:
            return {"id": pk, **product}
        else:
            raise HTTPException(status_code=404, detail="Product not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_next_product_id():
    """Increment a counter stored in Redis"""
    return redis_client.incr("product_counter")


@app.post("/product")
async def create_product(product: Product):
    try:
        product_id = get_next_product_id()
        redis_key = f"product:{product_id}"
        redis_client.hset(redis_key, mapping={
            "name": product.name,
            "price": product.price,
            "quantity": product.quantity
        })

        return {"product_id": product_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/product/{pk}")
def delete_product(pk: str):
    product_key = f"product:{pk}"

    if not redis_client.exists(product_key):
        raise HTTPException(status_code=404, detail=f"Product with id={pk} is not exists")

    redis_client.delete(product_key)

    return {"message": f"Product with id={pk} is deleted"}
